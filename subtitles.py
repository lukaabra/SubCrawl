import json
import gzip
import os
import base64
from socket import gaierror
from http.client import ResponseNotReady
from xmlrpc.client import ServerProxy, ProtocolError, Fault, expat


class SubtitlePreference(object):
    """
    Saves the users preferences for subtitle downloading, be it a selected language or sources from which to download
    selected subtitles.
    """

    def __init__(self):
        """
        Defaults the language to Albanian if the user does not select any language.
        """
        self.language_name = "Albanian"
        self.language_iso2 = "sq"
        self.language_iso3 = "alb"
        self.sub_source_preference = ("OpenSubtitles", "SubDB")

    def add_language(self, language_preference: str):
        """
        Adds the selected language to the class from a file which contains the list of all ISO639 languages.

        :param language_preference: (string) selected language from the combo box on the UI
        """
        with open("resources/iso 639 2.json", "r") as languages_file:
            languages_json = json.load(languages_file)
            for language in languages_json:
                if language_preference == language["English_Name"]:
                    self.language_name = language["English_Name"]
                    self.language_iso2 = language["Alpha2_Code"]
                    self.language_iso3 = language["Alpha3b_Code"]

    def change_sub_source(self, sub_source_list: list):
        """
        Changes the source of subtitle downloading depending on what the user ticked in the checkbox in the GUI. The
        tuple will be either one element or two elements long.
        TODO: Add to use

        :param sub_source_list: (list) list containing sources
        """
        self.sub_source_preference = tuple(sub_source_list)

    def __str__(self):
        return "Subtitle language preference:\t{0.language_name} - {0.language_iso2} - {0.language_iso3}\n" \
               "Subtitle sources preference: {0.sub_source_preference}\n".format(self)


class SubtitleDownloader(object):

    """
    Class for downloading subtitles. It's data attributes contain various information necessary for clarity and
    easy access.
    The class is instantiated with the preferences needed to operate (language preference, download sources, prompt
    to display information on and progress bar which to update). Then the downloading method is called which in turn
    does all the heavy lifting.
    """

    def __init__(self, subtitle_preference: SubtitlePreference, prompt_label, progress_bar, interactor):
        """
        :param subtitle_preference: (SubtitlePreference) signals from which sources to download and in what language
        :param prompt_label: (PromptLabel) label to which information during downloading will be displayed
        :param progress_bar: (ProgressBar) progress bar which is updated with the progression of downloading
        :param interactor: (_DB_Interactor) interacts with the database to retrieve information
        """
        self.preference = subtitle_preference
        self.prompt_label = prompt_label
        self.progress_bar = progress_bar
        self.interactor = interactor
        self.downloaded_files = 0

        # Token to log in to OpenSubtitles
        self.opensubs_token = None
        self.sub_file_extensions = (".RAR", ".ZIP", ".SRT")

    def _create_payload_for_subtitle_searching(self, entry: tuple) -> dict:
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
            payload_for_sub_search = dict()
        else:
            # If "imdbid" is defined, "query" is ignored.
            payload_for_sub_search = {"imdbid": entry_id,
                                      "query": entry_title,
                                      "sublanguageid": self.preference.language_iso3,
                                      "movie directory": movie_directory}
        return payload_for_sub_search

    def _perform_query_and_store(self, payload_for_sub_search: dict, proxy: ServerProxy):
        """
        Searches for the desired subtitles through the OpenSubtitles API and writes the download URL information
        to a table ("search_subs").

        :param payload_for_sub_search: (dictionary) contains the information about the movie for which
                                                    the subtitle will download
        :param proxy: ServerProxy.LogIn(username, password, language, useragent)

        :return download_data: (dictionary) contains crucial information for file downloading
        """
        try:
            query_result = proxy.SearchSubtitles(self.opensubs_token, [payload_for_sub_search], {"limit": 10})
        except Fault:
            self.prompt_label.setText("A fault has occurred")
        except ProtocolError:
            self.prompt_label.setText("A ProtocolError has occurred.")
        else:
            if query_result["status"] == "200 OK":
                if query_result["data"]:
                    payload_for_download = self._create_download_data(query_result["data"], payload_for_sub_search)
                    self.interactor.add_subtitle_search_data_to_db(payload_for_download)
                else:
                    self.prompt_label.setText("There is no subtitles in this language for {}".
                                              format(payload_for_sub_search["query"]))
            else:
                self.prompt_label.setText("Wrong status code: {}".format(query_result["status"]))

    def _create_download_data(self, query_results: dict, payload_for_sub_search: dict):
        """
        Creates the subtitle download data from the results of the OpenSubtitles server query

        :param query_results: (list) list of dictionaries containing information regarding queried subtitles
        :param payload_for_sub_search: (dict) payload created for the OpenSubtitles server query
        """
        for result in query_results:
            subtitle_name, download_link, sub_id = result["SubFileName"], result["SubDownloadLink"], result["IDSubtitleFile"]
            movie_id = payload_for_sub_search["imdbid"]
            movie_directory = payload_for_sub_search["movie directory"]
            if subtitle_name.upper().endswith(self.sub_file_extensions):
                payload_for_download = {"imdbid": movie_id,
                                        "file name": subtitle_name,
                                        "IDSubtitleFile": sub_id,
                                        "movie directory": movie_directory}
                return payload_for_download

    def _perform_file_download(self, proxy):
        """
        Creates a list of subtitle file ID's that the user has selected to download. Those ID's are passed to a function
        which will download the subtitle file byte code data and save to a file in the movie directory in chunks of
        20 files at a time (OpenSubtitle API restriction).

        :param proxy: (ServerProxy)
        """
        # Get subtitle information to download
        subtitle_ids = [sub_id for sub_id, _, __, ___ in self.interactor.retrieve("search_subs")]
        while len(subtitle_ids) >= 19:
            self._download_file(proxy, subtitle_ids[:19])
            subtitle_ids = subtitle_ids[19:]
            print(len(subtitle_ids))
        if subtitle_ids:
            self._download_file(proxy, subtitle_ids)

    def _download_file(self, proxy, subtitle_ids):
        """
        Tries to download byte data. If successful the data will be stored to a table in the database. Afterwards, that
        same data will be taken from that table and another table and written to a file.
        """
        download_data = dict()
        try:
            download_data = proxy.DownloadSubtitles(self.opensubs_token, subtitle_ids)
        except ProtocolError as e:
            download_data["status"] = e
            self.prompt_label.setText("There has been a ProtocolError during downloading")
        except ResponseNotReady as e:
            download_data["status"] = e
            self.prompt_label.setText("There has been a ResponseNotReady Error during downloading")

        if download_data["status"] == "200 OK":
            self._store_byte_data_to_db(download_data)
            self._get_stored_byte_data()
        else:
            self.prompt_label.setText("There was an error while trying to download your file: {}"
                                      .format(download_data["status"]))

    def _store_byte_data_to_db(self, download_data):
        for individual_download_dict in download_data["data"]:
            self.interactor.add_subtitle_download_data_to_db(tuple(individual_download_dict.values()))
        self.interactor.commit_and_renew_cursor()

    def _get_stored_byte_data(self):
        for sub_id, byte_data in self.interactor.retrieve("download_subs"):
            search_condition = ("subs_id", sub_id)
            # Get subtitle file name and movie directory path from another table
            for _, __, sub_name, movie_directory in self.interactor.retrieve("search_subs", search_condition):
                subtitle_path = movie_directory + "\\" + sub_name + ".gzip"
                self._write_file(byte_data, subtitle_path)
                break

    def _write_file(self, byte_data: str, subtitle_path: str):
        """
        Encode the byte_data string to bytes (since it's not in byte format by default) and write it to a .gzip
        file. Unzip the content of the .gzip file and write it outside (unzipped).

        :param byte_data: (string) string containing bytecode information
                                        ATTENTION: variable is not byte encoded, which is why it is done in this method
        :param subtitle_path: (string) absolute path where to write the subtitle
        """
        with open(subtitle_path, "wb") as subtitle_file:
            subtitle_file.write(base64.decodebytes(byte_data.encode()))

        # Open and read the compressed file and write it outside
        with gzip.open(subtitle_path, 'rb') as gzip_file:
            content = gzip_file.read()
            # Removes the ".gzip" extension
            with open(subtitle_path[:-4], 'wb') as srt_file:
                srt_file.write(content)

        self.downloaded_files += 1
        # Remove the .gzip file
        os.remove(subtitle_path)

    def download_from_opensubtitles(self):
        """
        Logs the user into the OpenSubtitles API. If the log in is successful then payloads are created for querying
        the OpenSubtitles database. The query result is passed to the download function. Meanwhile the Prompt Label in
        the GUI is updated with information.
        After all the downloading and querying is finished, the user is logged out.
        """
        with ServerProxy("https://api.opensubtitles.org/xml-rpc") as proxy:
            self.opensubs_token = self.log_in_opensubtitles(proxy)

            if self.opensubs_token != "error":
                self.prompt_label.setText("Connected to OpenSubtitles database")

                for payload_for_sub_search in (self._create_payload_for_subtitle_searching(entry)
                                               for entry in self.interactor.retrieve("selected_movies")):
                    # Removes the movie directory path from the payload which will be sent to OpenSubtitles
                    self._perform_query_and_store(payload_for_sub_search, proxy)

                self.interactor.commit_and_renew_cursor()

                self._perform_file_download(proxy)

                self.interactor.clear_db("search_subs")
                self.interactor.clear_db("download_subs")

                self.prompt_label.setText("Finishing up ...")
                proxy.LogOut(self.opensubs_token)
                self.prompt_label.setText("Download finished! Downloaded {} files".format(self.downloaded_files))

        self.downloaded_files = 0

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
        except gaierror:
            self.prompt_label.setText("Please check your internet connection and try again")
            return "error"
        except Exception as e:
            self.prompt_label.setText("Be sure to send us this error: {}".format(str(e)))
            return "error"
        else:
            if login["status"] == "200 OK":
                return login["token"]
            else:
                return "error"
