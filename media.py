import re
import requests
import json
import os
import random


class Media(object):

    def __init__(self, file_path: str):
        """
        An object which represents some for of media file. Most of the data attributes are pretty self-
        explanatory.

        :param file_path: (string) an absolute path of the media file

        movie_regex: (tuple) number of regular expressions with which we check the type of media
        """
        self.path = file_path
        self.folder_name, self.file_name = os.path.split(self.path)
        self.title, self.extension = os.path.splitext(self.file_name)
        self.subtitles = False
        self.sub_path = ()
        self.sub_language = []
        self.id = random.randint(1, 10000)
        self.imdb_rating = 0
        self.year = ""
        self.movie_regex = re.compile(r"(.*?[.| ])(\(\d{4}\)|\d{4}|\[\d{4}\])?([.| ].*)")

    def add_subs(self, sub_path: tuple):
        """
        Adds the passed folder as the subtitle path for this instance of the Media object.

        :param sub_path: (tuple) a tuple of absolute paths of the subtitle file/s
        """
        self.subtitles = True
        self.sub_path = sub_path

    def search_imdb_id(self) -> bool:
        """
        Searches through the OMDb API with the API key for a title and year. Returns a response
        which is transformed into text form (JSON)

        :return: (bool) Value if the response of the query was received.
        TODO: Make the requests an asynchronous operation.
        """
        media_type = "movie"
        # Key found on email
        url = "http://www.omdbapi.com/?apikey=678bc96c&t={0.title}&y={0.year}&type={1}".format(self, media_type)
        # Checks for internet connection
        response = requests.get(url)
        media_info = json.loads(response.text)

        try:
            self.id = media_info["imdbID"]
            self.title = media_info["Title"]
            self.year = media_info["Year"]
            self.imdb_rating = [item["Value"] for item in media_info["Ratings"] if item["Source"] ==
                                "Internet Movie Database"][0]
        except KeyError:
            # TODO: Consider adding a log of movies that were not found
            self.id = ""
        finally:
            return media_info["Response"]

    def __str__(self) -> str:
        """
        String representation of the object instance.
        """
        return "ID: {0.id}\nName: {0.file_name}\nPath: {0.path}\nTitle: {0.title}\nFile type: {0.extension}" \
               "\nSubtitles: {0.subtitles}\nSubtitle language: {0.sub_language}\n\
               Subtitle location: {0.sub_path}\n\n".format(self)


class Movie(Media):

    def __init__(self, file_path: str):
        super().__init__(file_path=file_path)

    def add_subs(self, sub_path: tuple):
        super().add_subs(sub_path=sub_path)

    def extract_movie_info(self):
        """
        Several regular expressions specifically targeted to find the titles of movies from
        irregularly written ones. re.search is used because we want to match the regular expression
        throughout the string, not just the beginning that re.match would do.

        The year_match checks for the year after the title of the movie. For now it works only
        on movies. Example of titles it works on:
            "The Killing of a Sacred Deer.2017.1080p.WEB-DL.H264.AC3-EVO[EtHD]"
            "12 Angry Men 1957 1080p BluRay x264 AAC - Ozlem"
            "Life.Is.Beautiful.1997.1080p.BluRay.x264.anoXmous"

        TODO: Full proof regexes and write more of them.
        """
        if self.movie_regex.search(self.title) is not None:
            try:
                self.year = self.movie_regex.search(self.title).group(2).strip()
            except AttributeError:
                self.year = ""
            finally:
                self.title = self.movie_regex.search(self.title).group(1).strip()
                additional_regex = re.compile(r"(.*)(\[.*\])")
                if additional_regex.search(self.title) is not None:
                    self.title = additional_regex.search(self.title).group(1)

    def search_imdb_id(self) -> None or str:
        return super().search_imdb_id()

    def __str__(self) -> str:
        """
        String representation of the object instance.
        """
        return "Title: {0.title}\nYear: {0.year}\nMovie IMDb ID: {0.id}\nFile name: {0.file_name}\n" \
               "Path: {0.path}\nFile type: {0.extension}\nSubtitles: {0.subtitles}\n" \
               "Subtitle language: {0.sub_language}\nSubtitle location: {0.sub_path}\n\n".format(self)
