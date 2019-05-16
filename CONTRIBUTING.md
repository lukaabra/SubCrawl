# Welcome contributor!

Thank you for checking out the project and deciding that it would be a good idea to contribute and fix it up. Because let's be honest, the project is a fixer-upper if there's ever been one. We appreciate the time you have set apart in learning more about SubCrawl. For further information check out our Wiki. Let's get down to business! :briefcase:

These guidelines are important as to develop this project in an organized fashion and help guide newcomers on the right path.

# SETTING UP

Currently you can set up SubCrawl to run by forking the repository to your designated folder and running `main.py`. Since this project is currently in it's beginning this is not how it is imagined it would run. You can view the vision and plan for the project on the [Wiki](https://github.com/lukaabra/SubCrawl/wiki/Vision). :telescope:

### Requirements:

- Python 3 - version 3.7.1
- [PyQt5](https://pypi.org/project/PyQt5/) - version: 5.11.3

Also an internet connection is needed to fetch data from OMDb and OpenSubtitles servers. This project uses a module [PTN (parse-torrent-name)](https://github.com/divijbindlish/parse-torrent-name) which is included as a submodule. :mega:

# CODE OF CONDUCT

You can check out our Code of Conduct [here](https://github.com/lukaabra/SubCrawl/blob/master/CODE_OF_CONDUCT.md). :page_with_curl:

# DISCLAIMER

:exclamation:

As mentioned in the README file, this project serves primarily as a platform to learn programming, Python, and developing in cooperation with the community. Things may not be done professionally at first, but we are here to learn and teach. :books: Any suggestions on improvement are more than welcome if they are properly and politely articulated. :speech_balloon:

# CONTRIBUTING

It a good practice to comment on an issue you want to take over so it is assigned to you. The reason for this is that it is possible you [fork](https://guides.github.com/activities/forking/) the repository and make a lot of changes to the code, only to find out later on that your [pull request](https://help.github.com/en/articles/creating-a-pull-request) has been rejected for God knows what reasons. To prevent this, reach out and ask to be assigned to an issue. :raising_hand: You can also open a new issue you found and ask to be assigned to it.
There is no need to ask for assignment on issues which include:

- Spelling / grammar fixes
- Typo correction, white space and formatting changes
- Comment clean up

If the maintainers of the repository do not answer immediately, please have patience. They will contact you as soon as possible. :pray:

### Commits

Commit messages should contain useful information regarding the changes made. Everyone was guilty at one point of committing `fixed crash` or `removed bug`. Strive for concise and clear documentation. Check out [this](https://medium.com/@andrewhowdencom/anatomy-of-a-good-commit-message-acd9c4490437) guide for more information. :pencil2:

# FIRST TIMERS

Under the [issues] tab you can find a whole lot of open problems with the project. I am absolutely sure you are capable of solving at least one problem from the list. Be sure to check those marked with **good first issue**. :school_satchel: If it does not look like it now, just fork the repository and go through the code. Documentation is still lacking at places but the general flow of the program is relatively understandable. I am sure even if you are not able to solve any kind of issue, you will find another one.

# LABELING ISSUES

Everyone is welcome to open new issues as soon as they find one. This includes the code, and also the documentation files. Follow the label convention:

- **good first issue** People who are not familiar with the language and the code base are able to contribute and solve after a short amount of time studying the issue
- **enhancement** Enrich the project with new features which currently do not exist
- **question** Communicate with the community and agree to a most favourable solution
- **invalid** This should not be like it is and should be fixed/extended regardless of whether it is working or not
- **bug** This is not working and should be fixed
- **help wanted** Ask the community for help, be it someone else taking over, asking for resources to solve the issue or pointers on how to approach the problem, or simply you don't have the time to tackle this right now

# REPORTING BUGS

When reporting a bug :bug: please follow the recommended template:

1. What version of Python are you using (python --version)?
2. What operating system are you using?
3. What did you do?
4. What did you expect to see?
5. What did you see instead?

# TESTS

Currently there no tests for this project. It is an [open issue](https://github.com/lukaabra/SubCrawl/issues/7) which we hope will be addressed soon.

# DOCUMENTATION

### Code

This project is using the [PEP8](https://www.python.org/dev/peps/pep-0008/) style guide and all the contributors are urged to follow it.
All classes should be documented with the general usage of the class. Not to many detailed information regarding the usages of each method. Abstract the usage and tell the story of how this class is used. For example, instead of:

```
"""
This class calls _download_from_opensubtitles_ which then logs in using _login_opensubtitles_ and queries the...
"""
```

try something like:

```
"""
This class logs the user to the Opensubtitles servers and queries them...
"""
```

Also, be sure to indicate all the parameters and return values of each method, their general short description and type:

```
"""
...

:param payload_for_sub_search: (dictionary) contains the information about the movie for which
                                                    the subtitle will download
:param proxy: ServerProxy.LogIn(username, password, language, useragent)

:return download_data: (dictionary) contains crucial information for file downloading
"""
```

But most of all, strive for code which is self-explanatory.

### Repository

Create a pull request and describe what have you changed in the documentation. Please be sure to check out our [Wiki](https://github.com/lukaabra/SubCrawl/wiki/Vision) about the vision of the project, as to avoid conflicts in information between documentation files.
Any changes to the "Vision" of the final look and feel of the project should first be opened in an issue and discussed between the community. If the support is great enough, the changes will be approved.

## CONTACT

For any doubts or any extra information contact me at:

:email: lukaabramovic2@gmail.com

