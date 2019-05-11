import os
import re

from folder import Folder, File
from media import Movie
from db_interactor import _DBInteractor


class Scanner(object):

    def __init__(self, path: str, program_dir: str):
        """
        :param program_dir: (string) Specifies the directory in which the program is installed
        :param path: (string) absolute path of the folder which to scan
        """
        self.path = os.path.abspath(path)
        self._program_dir = program_dir
        self.interactor = _DBInteractor(self._program_dir)
        self.movie_extensions = self._get_media_files_extensions()

        self.current_folder = None
        self.current_file = None

    def _get_media_files_extensions(self) -> tuple:
        """
        Pulls out from a text file a list of all media file extensions

        :return movie_extension: (tuple) list of strings with the file extensions
        """
        os.chdir(self._program_dir)

        with open("resources\\file-extensions.txt", "r") as f:
            movie_extensions = re.findall(r"(\.\w*)", f.read())
        return tuple(movie_extensions)

    def perform_scan(self, progress_tuple: tuple):
        """
        Performs the necessary steps to scan the designated folder.

        :param progress_tuple: (tuple) -> (function, integer) tuple that contains a function to update a progress bar
                                and the number of total files in the selected folder
        """
        self._scan_folder(self.path, progress_tuple)
        self.interactor.commit_and_renew_cursor()

    def get_number_of_duplicate_files(self):
        return self.interactor.duplicate_files

    def _scan_folder(self, selected_folder: str, progress_tuple: tuple):
        """
        Walks through the given folder for any media file. When the media file is found, it is saved
        into a database. Once a database is created there is no need to repopulate it during every scan
        if the file still exists. The file is removed from the database if during the scan it is not in
        the folder it used to be. Same as if a new file appeared that was not there before.

        :param selected_folder: (string) path to the folder which is scanned
        :param progress_tuple: (tuple) -> (function, integer) tuple that contains a function to update a progress bar
                                and the number of total files in the selected folder
        """
        os.chdir(selected_folder)
        scanned_files = 0

        for folder_name, _, file_names in os.walk(selected_folder):
            self.current_folder = Folder(folder_name)

            for file_name in file_names:
                scanned_files += 1
                self._update_scanning_progress_bar(scanned_files, progress_tuple)
                self._create_children_for_current_folder(file_name)

            self._pair_media_and_subs()

        # Return back to the directory of the program
        os.chdir(self._program_dir)

    def _update_scanning_progress_bar(self, scanned_files: int, progress_tuple: tuple):
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

    def _create_children_for_current_folder(self, file_name):
        """
        If the file is a media file or if the file is a subtitle file it creates children for the
        "current_folder" Folder type.
        """
        if file_name.upper().endswith(self.movie_extensions) or file_name.upper().endswith((".RAR", ".ZIP", ".SRT")):
            current_file_name = os.path.join(self.current_folder.path, file_name)
            self.current_file = File(current_file_name)
            self.current_file.detect_media_or_sub(self.movie_extensions)
            self.current_folder.add_child(self.current_file)

    def _pair_media_and_subs(self):
        """
        Creates a tuple of subtitle file absolute paths and pairs them with the corresponding media file to the method
        which creates them into an object.
        """
        self.current_folder.lock_children()
        media_contains_subs = tuple([file.path for file in self.current_folder.children if file.is_sub])
        for file in self.current_folder.children:
            if file.is_media:
                self._create_media(file.path, media_contains_subs)

    def _create_media(self, file_path: str, media_contains_subs: tuple, table="all_movies"):
        """
        Creates a Media object with the provided file_name and folder_name. If the media is a movie then creates
        a Movie object, if it is a series it creates a Series object. Adds it to the table all_movies.
        TODO: Add Series object to media.py

        :param file_path: (string) absolute path of the current file
        :param media_contains_subs: (tuple) indicates if the media has subtitles by getting an absolute path of the subs as a tuple
        :param table: (string) table to which the object will be added
        """
        media = Movie(file_path)
        media.extract_movie_info()
        movie_found = True  # No internet connection
        # movie_found = media.search_imdb_id()
        if movie_found:
            if media_contains_subs:
                media.add_subs(media_contains_subs)
            self.interactor.add_media_to_db(media, table)
