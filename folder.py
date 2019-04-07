import os


class Folder(object):
    """
    Object which represents a folder in a PC. It has parents which should also be of type Folder and children which
    are of type File and stored in a list. When the children are locked, they are converted to a tuple and prevented
    from further changes.

    TODO: Remove unnecessary features of Folder and File class
    """

    def __init__(self, path: str):
        """
        Initiates data attributes to their default values and adds the name of the folder using regular expression.

        :param path: (string) absolute path of the folder
        """
        self.path = path
        _, self.folder_name = os.path.split(path)
        self.parent = None
        self.children = []
        self.files = None

    def add_parent(self, parent):
        """
        Adds a parent to this instance of the Folder object.

        :param parent: (Folder) parent of this instance of a Folder object
        """
        self.parent = parent

    def add_child(self, child):
        """
        Method used to add a child to this Folder. The child will be of type File which is the reason why this instance
        of the folder is added to it as a parent.
        Use only Folder methods for adding children and parents.

        :param child: (File) child inside of this instance of the folder
        """
        self.children.append(child)
        child.add_parent(self)

    def lock_children(self):
        """
        Turns the 'children' data attribute which is type list into a tuple and essentially prevents it from any
        further changes.
        """
        self.children = tuple(self.children)

    def __str__(self):
        return "Folder name:\t{0.folder_name}\nFolder path:\t{0.path}\n".format(self)


class File(object):
    """
    Object which represents a file in a PC. Has parents as well as extensions.
    """

    def __init__(self, path: str):
        """
        Converts the absolute path to a file name and the extension of the file using regular expressions.

        :param path: (string) absolute path to the file
        """
        self.path = path
        _, self.file_name = os.path.split(path)
        self.parent = None
        self.is_media = False
        self.is_sub = False
        self.file_name, self.extension = os.path.splitext(self.file_name)

    def add_parent(self, parent: Folder):
        """
        Adds the parent to the data attribute of this instance of the File object.

        :param parent: (Folder) parent in which this file is located
        """
        self.parent = parent

    def detect_type(self, movie_extensions):
        """
        Detects if the file is a media type file or a subtitle file.

        :param movie_extensions: (tuple) Tuple of all media extensions
        """
        if self.extension.upper() in movie_extensions:
            self.is_media = True
            self.is_sub = False
        else:
            self.is_sub = True
            self.is_media = False

    def __str__(self):
        return "Path:\t{0.path}\nParent:\t{0.parent}\n".format(self)
