import json
import gzip
import os
import asyncio
import aiohttp
import aiofiles
from xmlrpc.client import ServerProxy, ProtocolError, Fault, expat

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

    def __init__(self, subtitle_preference: SubtitlePreference, interactor: _DBInteractor, prompt_label):
        self.preference = subtitle_preference
        self.interactor = interactor
        self.prompt_label = prompt_label

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
                       "sublanguageid": self.preference.language_iso3}
        return payload, movie_directory

    async def _perform_query(self, payload, proxy):
        """
        Searches for the desired subtitles through the OpenSubtitles API and writes the download URL information
        to a table inside the database.

        :param payload: (dictionary) contains the information about the movie for which the subtitle will download
        :param proxy: ServerProxy.LogIn(username, password, language, useragent)
        """
        try:
            # query_result = proxy.SearchSubtitles(self.opensubs_token, [payload], {"limit": 10})
            query_coroutine = asyncio.coroutine(proxy.SearchSubtitles(self.opensubs_token, [payload], {"limit": 10}))
            query_task = asyncio.create_task(query_coroutine)
            query_result = await query_task
        except Fault as e:
            raise "A fault has occurred:\n{}".format(e)
        except ProtocolError as e:
            raise "A ProtocolError has occurred:\n{}".format(e)
        else:
            if query_result["status"] == "200 OK":
                results = query_result["data"]
                # Iterates through the results and breaks away when a satisfactory file has been found
                for result in results:
                    subtitle_name, download_link = result["SubFileName"], result["SubDownloadLink"]
                    if subtitle_name.upper().endswith(self.sub_file_extensions):
                        download_data = {"download link": download_link, "file name": subtitle_name}
                        self.interactor.add_subtitle_to_db(download_data, self.preference.language_iso3)
                        break
            else:
                print("Wrong status code: {}".format(query_result["status"]))

    async def _download_and_save_file(self, movie_directory):
        """
        Iterates through the download links gotten from OpenSubtitles and tries to download and save each file from
        each link asynchronously using aiohttp.

        :param movie_directory:
        """
        for entry in self.interactor.retrieve("sub_dl_links"):
            download_link, sub_name = entry["download link"], entry["file name"]
            # Download .gz subtitle file
            # https://stackoverflow.com/questions/35388332/how-to-download-images-with-aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(download_link) as response:
                    if response.status == 200:
                        subtitle_path = movie_directory + "\\" + sub_name + ".gz"
                        # Streaming the response content
                        subtitle_file = await aiofiles.open(subtitle_path, mode="wb")
                        while True:
                            chunk = await response.content.read(10)
                            if not chunk:
                                break
                            await subtitle_file.write(chunk)
                        await subtitle_file.close()
                    else:
                        self.prompt_label.setText("There was a problem while trying to obtain the subtitle file.")

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
            # If there were not errors while logging in
            if self.opensubs_token != "error":
                for payload, movie_directory in (self._create_payload(entry) for entry in
                                                 self.interactor.retrieve("selected_movies")):
                    await self._perform_query(payload, proxy)
                    if self.interactor.cursor.fetchone(self.interactor.retrieve("sub_dl_links")) is None:
                        table_is_empty = True
                    else:
                        table_is_empty = False
                    download_task = asyncio.create_task(self._download_and_save_file(movie_directory))
                    if table_is_empty:
                        await download_task

                proxy.LogOut(self.opensubs_token)

    def update_progress(self, scanned_files: int, progress_tuple: tuple):
        """
        A number of scanned files is passed, and a function that will update the progress bar (GUI) with the scanned
        number of files compared to the total.

        :param scanned_files: (integer) number of files scanned in the selected folder
        :param progress_tuple: (tuple) -> (function, integer) tuple that contains a function to update a progress bar
                                and the number of total files in the selected folder
        """
        update_fn = progress_tuple[0]
        total_files = progress_tuple[1]
        percent = round((scanned_files / total_files) * 100, 2)
        update_fn(percent)

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
            login = proxy.LogIn("", "", self.preference.language_iso3, "TemporaryUserAgent")
        except Fault:
            self.prompt_label.setText("There was a fault while logging in to OpenSubtitles. Please try again.")
            return "error"
        except ProtocolError:
            self.prompt_label.setText("There was an error with the server. Please try again later.")
            return "error"
        except ConnectionResetError or ConnectionError or ConnectionAbortedError or ConnectionRefusedError:
            self.prompt_label.setText("Please check your internet connection.")
            return "error"
        except expat.ExpatError:
            # https://stackoverflow.com/questions/3664084/xml-parser-syntax-error
            self.prompt_label.setText("The received payload is probably incorrect")
            return "error"
        except Exception as e:
            raise e
            self.prompt_label.setText(str(e))
            return "error"
        else:
            if login["status"] == "200 OK":
                return login["token"]
            else:
                return "error"
