import json
from xmlrpc.client import ServerProxy, Error
import gzip, shutil
import urllib.request


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
        with open("iso 639 2.json", "r") as languages_file:
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

    def __init__(self, subtitle_preference):
        self.preference = subtitle_preference

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
        login = proxy.LogIn("", "", "", "TemporaryUserAgent")
        if login["status"] == "200 OK":
            return login["token"]
        else:
            return "Uh-oh! Something went wrong!"

    def download_from_opensubtitles(self):
        with ServerProxy("https://api.opensubtitles.org/xml-rpc") as proxy:
            language = ""
            token = self.log_in_opensubtitles(proxy)
            payload = {"query": "scarface",
                       "sub_language_id": language}
            results = proxy.SearchSubtitles(token, [payload], {"limit": 500})
            for result in results["data"]:
                sub_name = result["SubFileName"]
                download_link = result["SubDownloadLink"]
                subtitle_id = result["IDSubtitleFile"]
                break

            # Download .gz subtitle file
            urllib.request.urlretrieve(download_link, sub_name + ".gz")
            # Open and read the compressed file and write it outside
            with gzip.open(sub_name + ".gz", "rb") as f:
                file_content = f.read()
            with open(sub_name, "wb") as sub_file:
                sub_file.write(file_content)

            proxy.LogOut(token)
