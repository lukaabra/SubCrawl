import sqlite3
import os

from media import Media


class _DBInteractor(object):

    def __init__(self, program_dir: str, rom_mode=False):
        """
        Connects to a database and creates a cursor. Creates table all_movies if it does not exist.

        The all_movies table is for all of the media encountered in the scanned folder.
        The selected_movies is only for media which has been selected for subtitle downloading

        :param program_dir: (string) Specifies the directory in which the program is installed
        :param rom_mode: (Boolean) Specifies if the database will be open in Read Only Mode or not
        """
        self._program_dir = program_dir
        os.chdir(self._program_dir)
        self.db_name = "media.db"
        self.db = None
        self.cursor = None
        self.duplicate_files = 0

        if rom_mode:
            current_path = os.getcwd()
            try:
                # Opens the file in read only mode
                self.db = sqlite3.connect("file:{}\media.db?mode=ro".format(current_path), uri=True)
            # Database does not exist
            except sqlite3.OperationalError:
                self._establish_connection()
        else:
            self._establish_connection()

        self._create_tables()

    def add_media_to_db(self, media: Media, table="all_movies"):
        """
        Adds the file name, path, extension of the file, title, if there are any subtitles (bool in Python and
        int in SQLite3) and subtitle language string to the database.

        :param media: (Media) Media object of the file to add to the database or
        :param table: (string) table to which to add - "all_movies" or "selected_movies"
        """
        if self._check_duplicate(media, table):
            update_sql = "INSERT INTO {}(id, file_name, path, extension, title, year, rating, subtitles, sub_language)\
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)".format(table)
            self.cursor.execute(update_sql, (media.id, media.file_name, media.path, media.extension,
                                             media.title, media.year, media.imdb_rating,
                                             str(media.subtitles), " ".join(media.sub_language)))

    def _check_duplicate(self, media: Media, table="all_movies") -> tuple or None:
        """
        Checks for any duplicates in the database by first checking the file path and then the IMDb movie ID.

        :param media: (Media) Media object to check
        :param table: (string) name of the table in the database

        :return: True if there is no duplicate and None if a duplicate exists
        """
        # Checks if there is already an entry with this specific info
        look_up_string = "SELECT * FROM {} WHERE {}=?"
        look_up = look_up_string.format(table, "path")
        self.cursor.execute(look_up, (media.path, ))
        first_duplicate_check = self.cursor.fetchone()

        if first_duplicate_check is None:
            look_up = look_up_string.format(table, "id")
            self.cursor.execute(look_up, (media.id, ))
            second_duplicate_check = self.cursor.fetchone()
            if second_duplicate_check is None:
                return True
            else:
                self.duplicate_files += 1
                return None
        else:
            self.duplicate_files += 1
            return None

    def check_if_entries_exist(self, table="all_movies"):
        """
        Runs whenever the app is started. Checks if the entries in the database still exist.
        """
        for entry in self.retrieve(table):
            file_path = entry[2]
            if not os.path.isfile(file_path):
                condition = ("path", file_path)
                self.delete_entry(condition)

    def clear_db(self, table="all_movies"):
        """
        Clears the whole database of any data and entries inside.
        """
        clear_command = "DROP TABLE IF EXISTS {}".format(table)
        self.cursor.execute(clear_command)
        self._create_tables()

    def _close_and_commit_db(self):
        """
        Method that commits the changes done to the database and closes it up.
        """
        self.cursor.connection.commit()
        self.cursor.close()
        self.db.close()

    def _create_tables(self):
        """
        Creates tables "all_movies" and "selected_movies" if they do not exist.
        """
        # Subtitles is type INTEGER because SQLite3 does not support Boolean types
        all_movies_table = "CREATE TABLE IF NOT EXISTS all_movies(id INTEGER PRIMARY KEY NOT NULL, " \
                           "file_name TEXT NOT NULL, path TEXT NOT NULL, extension TEXT, title TEXT NOT NULL, " \
                           "year TEXT, rating TEXT, subtitles TEXT NOT NULL, sub_language TEXT)"
        selected_movies_table = "CREATE TABLE IF NOT EXISTS selected_movies(id INTEGER PRIMARY KEY NOT NULL, " \
                                "file_name TEXT, path TEXT, extension TEXT, title TEXT, " \
                                "year TEXT, rating TEXT, subtitles TEXT, sub_language TEXT)"
        self.cursor.execute(all_movies_table)
        self.cursor.execute(selected_movies_table)

    def commit_and_renew_cursor(self):
        """
        Commits changes to the database, closes it and renews the cursor.
        """
        self._close_and_commit_db()
        self._establish_connection()

    def copy_to_table(self, table_from, table_to, condition):
        """
        Copies entries from "table_from" to "table_to" that satisfy the field condition.

        :param table_from: (String) name of table from which to copy values
        :param table_to: (string) name of table to which to copy values
        :param condition: (tuple) Tuple with two entries which specify the search condition. Example:
                                    ("id", "12345")     The first element is the column and the second is the value.
        """
        sql_command = "INSERT INTO {} SELECT * FROM {}".format(table_to, table_from)
        conditional = " WHERE {}=?".format(condition[0])
        try:
            self.cursor.execute(sql_command + conditional, (condition[1], ))
        except sqlite3.IntegrityError:
            pass

    def delete_entry(self, condition, table="all_movies"):
        """
        Deletes an entry from the database that matches the passed condition.

        :param table: (string) A string specifying from which table to retrieve information
        :param condition: (tuple) Tuple with two entries which specify the search condition. Example:
                                    ("id", "12345")     The first element is the column and the second is the value.
        """
        if_statement = " WHERE {}=?".format(condition[0])
        sql_command = "DELETE FROM {}".format(table)
        self.cursor.execute(sql_command + if_statement, (condition[1], ))

    def _establish_connection(self):
        """
        Connects to the database and renews the cursor.
        """
        self.db = sqlite3.connect(self.db_name)
        self.cursor = self.db.cursor()

    def retrieve(self, table="all_movies", condition=None):
        """
        Retrieves entries from the database. It would be desirable if the database is only being opened for retrieving
        to connect to in in ROM mode(__init__).

        :param table: (string) A string specifying from which table to retrieve information
        :param condition: (tuple) Tuple with two entries which specify the search condition. Example:
                                    ("id", "12345")     The first element is the column and the second is the value.
        """
        self._establish_connection()
        if condition:
            if_statement = " WHERE {}=?".format(condition[0])
            result = self.cursor.execute("SELECT * FROM {}".format(table) + if_statement, (condition[1], ))
            search_result = [entry for entry in result]
            return tuple(search_result)
        else:
            self.cursor.execute("SELECT * FROM {}".format(table))
            return self.cursor.fetchall()
