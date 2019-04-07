# **SubCrawl**

##### Application for easy scanning of directories for movie files and subtitle downloading.

The application enables the user to scan a designated directory for movies. 
The application can recognize what file is a movie and can recognize which movie has subtitles. 
After the scanning part is completed, the user can choose which individual movies for which to download the 
subtitles in the selected language, or can simply select all the movies. 
There is also an option to select from which source to download the subtitles if they are available.

The whole application is built in Python 3. The GUI is built with PyQt5 and is designed in QtDesigner.
Each Python file holds classes which are grouped together thematically:


* **main.py** class MyApp in which the GUI is initialized and all the other methods from the other classes are binded

* **scanner.py** class Scanner who's task is to scan a designated folder for files and directories* 

* **folder.py** classes Folder and File which help organize the structure of the traversal of files and directories in scanner.py

* **media.py** classes Media and Movie which are in charge of verifying that the media file is a movie and organizing its data

* **subtitles.py** class SubtitlePreference which saves the language and source preference that the user chooses

* **db_interactor.py** class _DBInteractor which is in charge of database interaction, be it storing or retrieving entries
