import json
import gzip
import shutil
import os
import requests
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

    """
    Class for downloading subtitles. It's data attributes contain various information necessary for clarity and
    easy access. Data attributes are divided into 3 categories:
        * GUI and user interaction (prompt label and progress bar)
        * download variables (log in token, subtitle file extension list, etc.)
    """

    def __init__(self, subtitle_preference: SubtitlePreference, prompt_label, progress_bar):
        self.preference = subtitle_preference
        self.prompt_label = prompt_label
        self.progress_bar = progress_bar
        self.downloaded_files = 0

        self.opensubs_token = None
        self.payload = dict()
        self.sub_file_extensions = (".RAR", ".ZIP", ".SRT")

    def _create_payload(self, entry: tuple) -> tuple:
        """
        Creates a payload consisting of IMDbID, movie title and subtitle language data ready for downloading.

        :param entry: (tuple) tuple consisting of fields of a record from the database
        :return payload: (dictionary) information crucial for subtitle downloading for that particular movie
                movie_directory: (str) absolute path of the movie for which the subs will be downloaded
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

    def _perform_query(self, payload: dict, proxy: ServerProxy) -> dict:
        """
        Searches for the desired subtitles through the OpenSubtitles API and writes the download URL information
        to a dictionary which is then returned

        :param payload: (dictionary) contains the information about the movie for which the subtitle will download
        :param proxy: ServerProxy.LogIn(username, password, language, useragent)

        :return download_data: (dictionary) contains crucial information for file downloading
        """
        try:
            query_result = proxy.SearchSubtitles(self.opensubs_token, [payload], {"limit": 10})
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
                    movie_id = payload["imdbid"]
                    if subtitle_name.upper().endswith(self.sub_file_extensions):
                        download_data = {"imdbid": movie_id, "download link": download_link, "file name": subtitle_name}
                        return download_data
            else:
                print("Wrong status code: {}".format(query_result["status"]))

    def _download_and_save_file(self, movie_directory: str, query_result: dict):
        """
        If the response of the request to the file URL is okay it is written to a file in a stream of 128 kb. Else
        The error message is written on the prompt. During the streaming the progress bar is updated. Meanwhile the prompt
        is constantly being updated with information.

        :param movie_directory: (string) absolute path of the movie for which the subtitle file is being downloaded
        :param query_result (dictionary) result of the OpenSubtitles API with information crucial for downloading
        """
        download_link, sub_name = query_result["download link"], query_result["file name"]
        with requests.get(download_link) as response:
            if response.status_code == requests.codes.ok:
                subtitle_path = movie_directory + "\\" + sub_name + ".gz"
                self.prompt_label.setText("Beginning download of {}. Please wait".format(sub_name))
                # Stream the download 128 kb at a time and update the progress bar
                with open(subtitle_path, "wb") as sub_file:
                    for chunk in response.iter_content(chunk_size=128):
                        self.update_progress(len(chunk), (self.progress_bar.setValue, len(response.content)))
                        sub_file.write(chunk)
                self.downloaded_files += 1
                self.prompt_label.setText("Finished downloading {}".format(sub_name))

                # # Open and read the compressed file and write it outside
                # with gzip.open(subtitle_path, 'rb') as f_in:
                #     with open(subtitle_path, 'wb') as f_out:
                #         shutil.copyfileobj(f_in, f_out)

            elif response.raise_for_status() is not None:
                self.prompt_label.setText("{} Error while downloading {}".format(response.status_code, sub_name))

    def download_from_opensubtitles(self):
        """
        Logs the user into the OpenSubtitles API. If the log in successful then payloads are created for querying
        the OpenSubtitles database. The query result is passed to the download function. Meanwhile the Prompt Label in
        the GUI is updated with information.
        After all the downloading and querying is finished, the user is logged out.
        """
        with ServerProxy("https://api.opensubtitles.org/xml-rpc") as proxy:
            self.opensubs_token = self.log_in_opensubtitles(proxy)
            # If there were no errors while logging in
            if self.opensubs_token != "error":
                self.prompt_label.setText("Connected to OpenSubtitles database")
                for payload, movie_directory in (self._create_payload(entry) for entry in
                                                 self.interactor.retrieve("selected_movies")):
                    query_result = self._perform_query(payload, proxy)
                    self._download_and_save_file(movie_directory, query_result)

                self.prompt_label.setText("Finishing up ...")
                proxy.LogOut(self.opensubs_token)
                self.prompt_label.setText("Download finished! Downloaded {} files".format(self.downloaded_files))

    def update_progress(self, chunk_size: int, progress_tuple: tuple):
        """
        A number of scanned files is passed, and a function that will update the progress bar (GUI) with the scanned
        number of files compared to the total.

        :param chunk_size: (integer) number of files scanned in the selected folder
        :param progress_tuple: (tuple) -> (function, integer) tuple that contains a function to update a progress bar
                                and the number of total files in the selected folder
        """
        update_fn = progress_tuple[0]
        file_size = progress_tuple[1]
        percent = round((chunk_size / file_size) * 100, 2)
        update_fn(percent)

    def log_in_opensubtitles(self, proxy: ServerProxy) -> str:
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
            self.prompt_label.setText("Logging in to OpenSubtitles, please wait ...")
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
