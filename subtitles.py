import json
import gzip
from urllib import error, request
import os
import asyncio
import aiohttp
import aiofiles
import time
from xmlrpc.client import ServerProxy, ProtocolError, Fault

from db_interactor import _DBInteractor


class SubtitlePreference(object):
    """
    Saves the users preferences for subtitle downloading, be it a selected language or sources from which to download
    selected subtitles.
    """

    def __init__(self):
        self.language_name = "Albanian"
        self.language_iso2 = "sq"
        self.language_iso3 = "alb"
        self.sub_source_preference = ("OpenSubtitles", "SubDB")

    def add_language(self, language_preference):
        with open("resources/iso 639 2.json", "r") as languages_file:
            languages_json = json.load(languages_file)
            for language in languages_json:
                if language_preference == language["English_Name"]:
                    self.language_name = language["English_Name"]
                    self.language_iso2 = language["Alpha2_Code"]
                    self.language_iso3 = language["Alpha3b_Code"]

    def change_sub_source(self, sub_source_list: list):
        self.sub_source_preference = tuple(sub_source_list)

    def __str__(self):
        return "Subtitle language preference:\t{0.language_name} - {0.language_iso2} - {0.language_iso3}\n" \
               "Subtitle sources preference: {0.sub_source_preference}\n".format(self)


class SubtitleDownloader(object):

    def __init__(self, subtitle_preference: SubtitlePreference, interactor: _DBInteractor):
        self.preference = subtitle_preference
        self.interactor = interactor

        self.opensubs_token = None
        self.payload = dict()
        
        self.sub_file_extensions = (".RAR", ".ZIP", ".SRT")
        self.download_links_json_file_path = os.getcwd() + "\\resources\\dl_links.json"

    def _create_payload(self, entry):
        """
        Creates a payload consisting of IMDbID, movie title and subtitle language data ready for downloading.

        :param entry: (tuple) tuple consisting of fields of a record from the database
        :return payload: (dictionary) information crucial for subtitle downloading for that particular movie
        """
        try:
            entry_id = entry[0]
            entry_title = entry[4]
            movie_directory, _ = os.path.split(entry[2])
        except KeyError:
            payload = dict()
            movie_directory = ""
        else:
            # If "imdbid" is defined, "query" is ignored.
            payload = {"imdbid": entry_id,
                       "query": entry_title,
                       "sub_language_id": self.preference.language_iso3}
        return payload, movie_directory

    def _perform_query(self, payload, proxy):
        """
        Searches for the desired subtitles through the OpenSubtitles API and writes the download URL information
        to a JSON file.

        :param payload: (dictionary) contains the information about the movie for which the subtitle will download
        :param proxy: ServerProxy.LogIn(username, password, language, useragent)
        """
        try:
            query_result = proxy.SearchSubtitles(self.opensubs_token, [payload], {"limit": 10})
        except Fault as e:
            raise "A fault has occurred:\n{}".format(e)
        except ProtocolError as e:
            raise "A ProtocolError has occurred:\n{}".format(e)
        else:
            if query_result["status"] == "200 OK":
                if os.path.isfile(self.download_links_json_file_path):
                    write_mode = "a"
                else:
                    write_mode = "w"
                with open("resources\\dl_links.json", write_mode) as dl_links_json:
                    results = query_result["data"]
                    for result in results:
                        subtitle_name, download_link = result["SubFileName"], result["SubDownloadLink"]
                        if subtitle_name.upper().endswith(self.sub_file_extensions):
                            download_data = {"download link": download_link, "file name": subtitle_name}
                            json.dump(download_data, dl_links_json)
                            break
            else:
                print("Wrong status code: {}".format(query_result["status"]))

    async def _download_and_save_file(self, movie_directory):
        """
        Iterates through the download links gotten from OpenSubtitles and tries to download and save each file from
        each link asynchronously using aiohttp.

        :param movie_directory:
        :return:
        """
        with open("resources\\dl_links.json", "r") as dl_links_json:
            file_data = json.load(dl_links_json)
            download_link, sub_name = file_data["download link"], file_data["file name"]
            # Download .gz subtitle file
            # https://stackoverflow.com/questions/35388332/how-to-download-images-with-aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(download_link) as response:
                    if response.status == 200:
                        subtitle_path = movie_directory + "\\" + sub_name + ".gz"
                        # Streaming the response content
                        with open(subtitle_path, "wb") as subtitle_file:
                            while True:
                                # TODO: Add to progress bar
                                chunk = await response.content.read(10)
                                if not chunk:
                                    break
                                subtitle_file.write(chunk)

        # Open and read the compressed file and write it outside
        # with gzip.open(sub_name + ".gz", "rb") as f:
        #     file_content = f.read()
        # with open(sub_name, "wb") as sub_file:
        #     sub_file.write(file_content)

    async def download_from_opensubtitles(self):
        """
        Logs the user into the OpenSubtitles API and performs the query of their servers. For each result of the query
        (for each selected movie) the program downloads the subtitle and saves it into the folder where the movie
        is located.
        The function tries to start doing queries for subtitle download URL's and then commence downloading the files
        from the URL's at the same time.
        """
        with ServerProxy("https://api.opensubtitles.org/xml-rpc") as proxy:
            self.opensubs_token = self.log_in_opensubtitles(proxy)
            for payload, movie_directory in (self._create_payload(entry) for entry in
                                             self.interactor.retrieve("selected_movies")):
                self._perform_query(payload, proxy)
                download_task = asyncio.create_task(self._download_and_save_file(movie_directory))
                await download_task
            os.remove(self.download_links_json_file_path)

            proxy.LogOut(self.opensubs_token)

    def log_in_opensubtitles(self, proxy):
        """
        Logs in the user to OpenSubtitles. This function should be called always when starting talking with server.
        It returns token, which must be used in later communication. If user has no account, blank username and
        password should be OK. As language - use ​ISO639 2 letter code.

        :param proxy: ServerProxy.LogIn(username, password, language, useragent)
                username: (string) Can be blank since anonymous users are allowed
                password: (string) Can be blank since anonymous users are allowed
                language: (string) Either HTTP ACCEPT-LANGUAGE header or ISO639 2
                useragent: (string) Use your registered useragent, also provide version number - we need tracking
                version numbers of your program. If your UA is not registered, you will get error 414 Unknown User Agent

        :return: token or error message

        Link to request useragent:
                http://trac.opensubtitles.org/projects/opensubtitles/wiki/DevReadFirst
        """
        try:
            login = proxy.LogIn("", "", "", "TemporaryUserAgent")
        except Fault as e:
            raise "A fault has occurred during log in:\n{}".format(e)
        except ProtocolError as e:
            raise "A ProtocolError has occurred during log in:\n{}".format(e)
        else:
            if login["status"] == "200 OK":
                return login["token"]
            else:
                return "Uh-oh! Something went wrong!"
