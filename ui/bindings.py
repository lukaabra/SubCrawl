from ui.gui import Ui_SubCrawl
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot

import os
import requests
import winsound
import json
import collections

from scanner import Scanner
from db_interactor import _DBInteractor
from subtitles import SubtitlePreference, SubtitleDownloader


class SubCrawl(Ui_SubCrawl, QtWidgets.QMainWindow):
    """
    Class which creates all the functions for the GUI to be operational. After the creation it also bind them together.

    """

    def __init__(self):
        Ui_SubCrawl.__init__(self)
        QtWidgets.QMainWindow.__init__(self)
        self.setupUi(self)
        self.showMaximized()

        # TODO: Implement enabling and disabling of buttons depending on the confirmation of selection
        self.selection_confirmed = False
        self.program_dir = os.getcwd()
        self.total_files = 0

        self.subtitle_preference = SubtitlePreference()
        self.interactor = _DBInteractor(self.program_dir)
        self.interactor.check_if_entries_exist()
        self._populate_table()

        self.subtitle_downloader = SubtitleDownloader(self.subtitle_preference, self.PromptLabel,
                                                      self.ProgressBar, self.interactor)

    @pyqtSlot()
    def _populate_table(self, db_table="all_movies", condition=None):
        """
        Goes through media.db database and populates the table if there are any entries in the database upon startup.

        media.db structure:

        all_movies & selected_movies:
        id     file_name     path     extension     title     year     rating     subtitles     sub_language

        :param db_table: (string) table in the database from which to populate
        :param condition: (tuple) Tuple with two entries which specify the search condition. Example:
                                    ("id", "12345")     The first element is the column and the second is the value.
        """
        self.ScannedItems.setRowCount(0)
        table_row = self.ScannedItems.rowCount()

        for entry in self.interactor.retrieve(db_table, condition):
            self._set_items_in_table(table_row, entry)
            self.ScannedItems.insertRow(table_row)
            table_row = self.ScannedItems.rowCount()

        # If the "Select All" radio button was checked before the table was populated (table was empty), call the
        # function that selects all the movies
        if self.SelectAllRadio.isChecked():
            self.select_all_movies(True)

    def _set_items_in_table(self, table_row: int, entry: tuple):
        """
        Fills up contents to the cells in that row.
        :param table_row: (int) row to fill up
        :param entry: (tuple) contents from the database
        """
        entry_id, _, entry_location, __, entry_title, entry_year, entry_rating, entry_subs, __ = entry

        self.ScannedItems.setItem(table_row, 0, QtWidgets.QTableWidgetItem(str(entry_id)))
        self.ScannedItems.setItem(table_row, 1, QtWidgets.QTableWidgetItem(entry_title))
        self.ScannedItems.setItem(table_row, 2, QtWidgets.QTableWidgetItem(entry_rating))
        self.ScannedItems.setItem(table_row, 3, QtWidgets.QTableWidgetItem(entry_year))
        self.ScannedItems.setItem(table_row, 4, QtWidgets.QTableWidgetItem(entry_location))
        # Boolean values must be written as string values to the GUI table
        self.ScannedItems.setItem(table_row, 5, QtWidgets.QTableWidgetItem(entry_subs))

    def bind_browse_button(self):
        """
        Connects the browse button to the method that opens the file dialog.
        """
        self.BrowseButton.clicked.connect(self.on_click_browse)

    @pyqtSlot()
    # Needed decorator to traverse some compatibility issues with Python and C++
    def on_click_browse(self):
        """
        Sets the default directory to the Desktop. Opens up a File Dialog in a mode where the user can only
        choose directories. The user chooses the directory which he wishes to scan and the absolute path to that
        directory is saved in the "SelectedFolderDisplay" text area.
        """
        self.PromptLabel.setText("Browsing...")
        # Sets the default directory of the FileDialog to "Desktop"
        directory = os.path.join(os.environ["HOMEPATH"], "Desktop")
        # Opens the file dialog to select only directories
        selected_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Open a folder",
                                                                  directory, QtWidgets.QFileDialog.ShowDirsOnly)
        # If no directory is chosen to scan, the program sets it back to default (Desktop)
        if selected_dir == "":
            selected_dir = directory
        # Updates the label with the selected folders absolute path
        self.SelectedFolderDisplay.setText(selected_dir)
        self.PromptLabel.setText("Folder selected")

    def bind_clear_button(self):
        """
        Connects the "Clear database" button to the method that deletes all the tables.
        """
        self.ClearDBButton.clicked.connect(self.on_click_clear_db)

    @pyqtSlot()
    def on_click_clear_db(self):
        """
        Deletes all the tables inside the database.
        """
        self.interactor.clear_db()
        self.interactor.clear_db("selected_movies")
        self.interactor.clear_db("search_subs")
        self.interactor.clear_db("download_subs")
        self.ScannedItems.setRowCount(0)
        self.interactor.commit_and_renew_cursor()
        self.PromptLabel.setText("Database cleared!")

    def bind_confirm_selection(self):
        self.ConfirmSelectionButton.clicked.connect(self.on_click_confirm_selection)

    def on_click_confirm_selection(self):
        """
        "Locks" the table (disables selection) and highlights the table to confirm that the selection has been
        carried out.
        """
        self.ScannedItems.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.CancelSelectionButton.setEnabled(True)
        self.ConfirmSelectionButton.setEnabled(False)
        self.DownloadButton.setEnabled(True)
        self.RemoveEntryButton.setEnabled(False)

        selected_rows = self.ScannedItems.selectionModel().selectedRows()
        for row in selected_rows:
            condition = ("id", str(row.data()))
            # The retrieve method here always returns a single record from the database since there is only one
            # record with that ID being passed to it.
            self.interactor.copy_to_table("all_movies", "selected_movies", condition)
        self.interactor.commit_and_renew_cursor()

        self.ScannedItems.setLineWidth(2)
        self.PromptLabel.setText("Selection confirmed!")

    def bind_cancel_selection(self):
        self.CancelSelectionButton.clicked.connect(self.on_click_cancel_selection)

    def on_click_cancel_selection(self):
        self.ScannedItems.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.CancelSelectionButton.setEnabled(False)
        self.ConfirmSelectionButton.setEnabled(True)
        self.RemoveEntryButton.setEnabled(False)
        self.DownloadButton.setEnabled(False)
        self.ScannedItems.setLineWidth(1)
        self.interactor.clear_db("selected_movies")
        self.PromptLabel.setText("Canceled selection")

    def bind_checkbox(self):
        self.OpenSubtitlesCheck.toggled.connect(self.checkbox_handler)
        self.SubsDbCheck.toggled.connect(self.checkbox_handler)

    def checkbox_handler(self):
        """
        Checks the state of each checkbox and accordingly changes the SubtitlePreference class instance.
        """
        if self.OpenSubtitlesCheck.isChecked():
            if self.SubsDbCheck.isChecked():
                self.subtitle_preference.sub_source_preference = ("OpenSubtitles", "SubsDB")
            else:
                self.subtitle_preference.sub_source_preference = ("OpenSubtitles",)
        elif self.SubsDbCheck.isChecked():
            self.subtitle_preference.sub_source_preference = ("SubsDB", )
        else:
            self.subtitle_preference.sub_source_preference = ()

    def bind_combo_box(self):
        """
        Connects the combo box to the function which changes the text on the label showing the language.
        """
        self.LanguageComboBox.activated.connect(self.on_click_language_combo_box)

    def on_click_language_combo_box(self):
        """
        Changes the LanguageLabel's text when another language is selected for the subtitles in the combobox.
        """
        selected_language = self.LanguageComboBox.currentText()
        self.LanguageLabel.setText("Language: {}".format(selected_language))
        self.subtitle_preference.add_language(selected_language)
        self.PromptLabel.setText("Subtitle language changed to {}".format(selected_language))

    def bind_download_button(self):
        self.DownloadButton.clicked.connect(self.on_click_download)

    def on_click_download(self):
        self.PromptLabel.setText("Commencing download ...")
        self.subtitle_downloader.download_from_opensubtitles()

    def bind_radio_buttons(self):
        """
        Connects the "view" radio buttons to the function that repopulates the GUI table.
        """
        self.ShowAllRadio.toggled.connect(self.view_radio_buttons)
        self.ShowNoSubsRadio.toggled.connect(self.view_radio_buttons)
        self.ShowSubsRadio.toggled.connect(self.view_radio_buttons)

        self.SelectAllRadio.toggled.connect(self.select_all_movies)

    @pyqtSlot()
    def view_radio_buttons(self):
        """
        Changes the items displayed in the table on the GUI depending on the Radio Buttons selected under the label
        "Table view:"
        """
        # Display all movies from the database
        if self.ShowAllRadio.isChecked():
            self.ScannedItems.setRowCount(0)
            self._populate_table("all_movies")

        # Display only movies without subtitles
        elif self.ShowNoSubsRadio.isChecked():
            self.ScannedItems.setRowCount(0)
            self._populate_table("all_movies", ("subtitles", str(False)))

        # Display only movies with subtitles
        elif self.ShowSubsRadio.isChecked():
            self.ScannedItems.setRowCount(0)
            self._populate_table("all_movies", ("subtitles", str(True)))

    def select_all_movies(self, checked: bool):
        """
        Selects all the movies in the GUI table creating a Qt item called SelectionRange.
        """
        table_range = QtWidgets.QTableWidgetSelectionRange(0, 0, self.ScannedItems.rowCount() - 1,
                                                           self.ScannedItems.columnCount() - 1)
        if checked:
            self.ScannedItems.setRangeSelected(table_range, True)
        else:
            self.ScannedItems.setRangeSelected(table_range, False)

    def bind_remove_entry(self):
        """
        Button to remove a selected entry in the table
        """
        self.RemoveEntryButton.clicked.connect(self.on_click_remove_entry)

    def on_click_remove_entry(self):
        """
        Deletes rows from the highest index to the lowest as to avoid bugs while iterating through the rows and
        deleting them at the same time.
        """
        selected_rows = self.ScannedItems.selectionModel().selectedRows()
        rows_to_delete = dict()
        for row in selected_rows:
            rows_to_delete[row.row()] = (row, row.data())

        # Creates an OrderedDict which preserves the order of its elements
        rows_to_delete = collections.OrderedDict(sorted(rows_to_delete.items(), reverse=True))
        for row in rows_to_delete:
            _, row_id = rows_to_delete[row]
            condition = ("id", row_id)
            self.interactor.delete_entry(condition)
            self.ScannedItems.removeRow(row)

        self.interactor.commit_and_renew_cursor()

    def bind_scan_button(self):
        """
        Connects the "Start scan" button to the scan method.
        """
        self.StartScanButton.clicked.connect(self.on_click_scan)

    @pyqtSlot()
    def on_click_scan(self):
        """
        A connection method for the "Start scan" button. Clicking the button initiates the scanning of the selected
        files, as well as the progress bar animation. The scanning function "perform_scan" is called from
        "scanner.py" in which the function for updating the progress bar is located.
        """
        # Resets the total amount of files scanned before each scan
        self.total_files = 0
        self._calculate_total_number_of_files()
        progress_tuple = (self.ScanProgressBar.setValue, self.total_files)

        # Initiate the Scanner object with the designated path
        scanner = Scanner(self.SelectedFolderDisplay.text(), self.program_dir)

        # Connection error is caught here and not in 'media.py' because it is easier to show an error message and alert
        # from 'main.py'
        self.PromptLabel.setText("Scanning...")
        try:
            self._disable_buttons()
            scanner.perform_scan(progress_tuple)
            duplicate_files = scanner.get_number_of_duplicate_files()

        except requests.ConnectionError:
            self._handle_error("There was a connection error! Please check your internet connection.")

        # _get_media_files_extensions not reading the .txt file
        except FileNotFoundError:
            self._handle_error("Oops! Unfortunately there was a problem!")

        except json.JSONDecodeError:
            self._handle_error("There is a problem with the internet connection. Try again later.")

        else:
            self.PromptLabel.setText("Folder scanning complete! {} files already exist in the database"
                                     .format(duplicate_files))
            self._populate_table("all_movies")

        finally:
            self._enable_buttons()

        self.ScanProgressBar.setValue(0)

    def _calculate_total_number_of_files(self):
        """
        Calculates the total number of files in the selected folder for the progress bar
        """
        for path, dirs, files in os.walk(self.SelectedFolderDisplay.text()):
            for _ in files:
                self.total_files += 1

    def _handle_error(self, message):
        winsound.MessageBeep()
        self.PromptLabel.setText(message)

    def bind_table_selection_changed(self):
        self.ScannedItems.itemSelectionChanged.connect(self.table_selection_function)

    def table_selection_function(self):
        """
        Each time an item is selected in the table, different buttons are enabled or disabled depending on the
        number of items selected. In addition, a labels text is also being changed representing the number of
        items selected in the GUI table.
        """
        selected_rows = self.ScannedItems.selectionModel().selectedRows()
        if not selected_rows:
            self.ConfirmSelectionButton.setEnabled(False)
            self.RemoveEntryButton.setEnabled(False)
        else:
            self.ConfirmSelectionButton.setEnabled(True)
            self.RemoveEntryButton.setEnabled(True)
        self.SelectedRowsCount.setText("{} movies selected".format(len(selected_rows)))

    def _disable_buttons(self):
        """
        Disables some buttons and enables 1. The list of buttons to disable is below:

        ClearDBButton
        DownloadButton
        StartScanButton
        BrowseButton

        Enabled button:

        CancelButton
        """
        self.ClearDBButton.setEnabled(False)
        self.DownloadButton.setEnabled(False)
        self.StartScanButton.setEnabled(False)
        self.BrowseButton.setEnabled(False)
        self.CancelButton.setEnabled(True)

    def _enable_buttons(self):
        """
        Enables some buttons and disables 1. The list of buttons to enable is below:

        ClearDBButton
        DownloadButton
        StartScanButton
        BrowseButton

        Disable button:

        CancelButton
        """
        self.ClearDBButton.setEnabled(True)
        self.DownloadButton.setEnabled(True)
        self.StartScanButton.setEnabled(True)
        self.BrowseButton.setEnabled(True)
        self.CancelButton.setEnabled(False)

    def populate_language_combo_box(self):
        """
        Clears the default values set in the QtDesigner for the Language Combo box and adds all the languages
        from ISO 639-2 contained in a single .json file
        """
        self.LanguageComboBox.clear()
        with open("resources\\iso 639 2.json", "r") as languages_file:
            languages_json = json.load(languages_file)
            languages_list = [language["English_Name"] for language in languages_json]
            self.LanguageComboBox.addItems(languages_list)
        self.LanguageLabel.setText("Language: {}".format(self.LanguageComboBox.itemText(0)))
