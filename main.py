from PyQt5 import QtWidgets

import sys
import os

from ui.bindings import SubCrawl


sys._excepthook = sys.excepthook


# Custom except hook used to detect program errors when PyQt crashes without error messages.
def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print(exctype, value, traceback)
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = my_exception_hook


def bind_all_buttons(application):
    # Binds the signals to the buttons
    application.bind_download_button()
    application.bind_browse_button()
    application.bind_scan_button()
    application.bind_clear_button()
    application.bind_radio_buttons()
    application.bind_combo_box()
    application.bind_confirm_selection()
    application.bind_cancel_selection()
    application.bind_table_selection_changed()
    application.bind_checkbox()
    application.bind_remove_entry()
    application.populate_language_combo_box()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SubCrawl()

    # Sets the default home directory to Desktop
    desktop_directory = os.path.join(os.environ["HOMEPATH"], "Desktop")
    window.SelectedFolderDisplay.setText(desktop_directory)
    bind_all_buttons(window)
    window.show()

    try:
        sys.exit(app.exec_())
    except:
        print("Exiting")

