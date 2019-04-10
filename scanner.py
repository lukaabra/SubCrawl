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

    def create_media(self, file_path: str, contains_subs: tuple, table="all_movies"):
        """
        Creates a Media object with the provided file_name and folder_name. If the media is a movie then creates
        a Movie object, if it is a series it creates a Series object. Adds it to the table all_movies.

        :param file_path: (string) absolute path of the current file
        :param contains_subs: (tuple) indicates if the media has subtitles by getting an absolute path of the subs as a tuple
        :param table: (string) table to which the object will be added
        """
        media = Movie(file_path)
        media.extract_movie_info()
        # movie_found = True  # No internet connection
        movie_found = media.search_imdb_id()
        if movie_found:
            if contains_subs:
                media.add_subs(contains_subs)
            self.interactor.add_media_to_db(media, table)

    def perform_scan(self, progress_tuple: tuple):
        """
        Performs the necessary steps to scan the designated folder.

        :param progress_tuple: (tuple) -> (function, integer) tuple that contains a function to update a progress bar
                                and the number of total files in the selected folder
        """
        self._scan_folder(self.path, self.video_files_extensions(), progress_tuple)
        self.interactor.commit_and_renew_cursor()
        return self.interactor.duplicate_files

    def _scan_folder(self, selected_folder: str, movie_extensions: tuple, progress_tuple: tuple):
        """
        Walks through the given folder for any media file. When the media file is found, it is saved
        into a database. Once a database is created there is no need to repopulate it during every scan
        if the file still exists. The file is removed from the database if during the scan it is not in
        the folder it used to be. Same as if a new file appeared that was not there before.

        :param selected_folder: (string) path to the folder which is scanned
        :param movie_extensions: (tuple) a list of strings containing common media file extensions
        :param progress_tuple: (tuple) -> (function, integer) tuple that contains a function to update a progress bar
                                and the number of total files in the selected folder
        """
        os.chdir(selected_folder)
        scanned_files = 0

        for folder_name, _, file_names in os.walk(selected_folder):
            current_folder = Folder(folder_name)

            for file_name in file_names:
                scanned_files += 1
                self.update_progress(scanned_files, progress_tuple)

                # If the file is a media file or if the file is a subtitle file it creates children for the
                # "current_folder" Folder type.
                if file_name.upper().endswith(movie_extensions) or file_name.upper().endswith((".RAR", ".ZIP", ".SRT")):
                    current_file = File(os.path.join(current_folder.path, file_name))
                    current_file.detect_type(movie_extensions)
                    current_folder.add_child(current_file)

            # Locks the Folder's children and makes a tuple of Boolean (True) values for every File that is a
            # subtitle file in the Folder's children.
            current_folder.lock_children()
            contains_subs = tuple([file.path for file in current_folder.children if file.is_sub])
            for file in current_folder.children:
                if file.is_media:
                    self.create_media(file.path, contains_subs)
                    # TODO: Check again scanning process for any weaknesses

        # Return back to the directory of the program
        os.chdir(self._program_dir)

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

    def video_files_extensions(self) -> tuple:
        """
        Pulls out from a text file a list of all media file extensions

        :return movie_extension: (tuple) list of strings with the file extensions
        """
        os.chdir(self._program_dir)

        with open("resources\\file-extensions.txt", "r") as f:
            movie_extensions = re.findall(r"(\.\w*)", f.read())
        return tuple(movie_extensions)
