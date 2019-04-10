# **SubCrawl**

##### Application for easy scanning of directories for movie files and subtitle downloading.

###What?

The application enables the user to scan a designated directory for movies. :tv:
The application can recognize what file is a movie and can recognize which movie has subtitles. :movie_camera:
After the scanning part is completed, the user can choose which individual movies for which to download the 
subtitles in the selected language, or can simply select all the movies. :japan:
There is also an option to select from which source to download the subtitles if they are available.

###Why?

This is a project I started as a way to learn Python 3 and to get familiar with the process of creating an application. I chose this theme because I could find use out of it. I know this type of application probably already exists and that is why I stated already that the primary reason for making this is to learn and grow as a developer. :mortar_board:

###How?

The whole application is built in Python 3. The GUI is built with PyQt5 and is designed in QtDesigner.
File names are parsed using a package called PTN (parse torrent name)

:mega: https://github.com/divijbindlish/parse-torrent-name

Each Python file holds classes which are grouped together thematically:


:star: **main.py** class MyApp in which the GUI is initialized and all the other methods from the other classes are bound

:fax: **scanner.py** class Scanner who's task is to scan a designated folder for files and directories

:file_folder: **folder.py** classes Folder and File which help organize the structure of the traversal of files and directories in scanner.py

:clapper: **media.py** classes Media and Movie which are in charge of verifying that the media file is a movie and organizing its data

:page_facing_up: **subtitles.py** class SubtitlePreference which saves the language and source preference that the user chooses

:floppy_disk: **db_interactor.py** class _DBInteractor which is in charge of database interaction, be it storing or retrieving entries

###Want to help?

If you are willing to get your hands dirty and learn as you work, do not hesitate. Contribute with anything you think will improve the application. Begginers and masters of the craft are welcomed to join! :muscle:

Check the open issues and start there. If you can't find anything of interest, let me know and we will find something! :question:

###Note

This project is not yet at a point where it can be used as intended. There are still some issues that need to be resolved before it can be used properly.
