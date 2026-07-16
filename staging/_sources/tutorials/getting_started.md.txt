<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Setting up Navigate
This is a beginner-level tutorial. The normal installation procedure for developers is mentioned in the `README.md`

Navigate can be run though a number of different editors, environments and IDEs since it us just a python package. In this tutorial, we will showcase using Visual Studio Code as it keeps the usage streamlined throughout operating systems and holds everything you need in one place.

## Prequisites:

- Python 3.12
- Visual Studio Code 

On windows, all of these programs can be downloaded without administrator privileges through the microsoft store.

### (Optional) Using an environment manager.

If you use python for other projects and want to maintain separate python environments, you need an environment manager. Examples include:
- [Conda](https://www.anaconda.com/docs/getting-started/miniconda/install) - Separate install
- [venv](https://docs.python.org/3/library/venv.html) - Comes with python.

Creating, activating and maintaining environments is neither part of, nor required for this tutorial, but a good practice in the future.

## Downloading the Software

Navigate is available [here!](https://github.com/zerocarbonshipping/navigate-zcs)

### Option 1 - I have never used git.

In the github repository, click green `<> Code` button and select *Download Zip*. Unzip the file and move the folder named `Navigate` to a location where you want to work with it.

### Option 2 - I use git.

Clone the repository at your desired location. 

## Installation and Setup

1. Open Visual Studio Code (VSCode) and open the `Navigate` folder in VS Code. 

2. Open up a new terminal VS Code or a terminal program of your choice.

3. Type `pip install .` into the terminal. If this doesn't work, you can also attempt `pip3 install .`. 

This tutorial also lives in the repository, under `docs/tutorials/`. You can open it and read along from there if you prefer.


## Basic Terminal Usage

If you have never used a terminal before, we will go through the prompt and two commands that you will often need in conjunction with Navigate.

The prompt shows you in which folder you are currently.
```bash
user@host:~/Navigate $
```
This prompt tells you that the user `user` is on the machine `host` in the folder `~/Navigate`. Yours may look different, but the path is almost always included.

**The ls command**
```bash
ls
```
This command lists all items in the current directory (folder). Example output:
```
CHANGELOG.md  CITATION.cff  CODESTYLE.md  CONTRIBUTING.md  LICENSE  Makefile  README.md  assumptions  docs  navigate  pyproject.toml  simulations  syntax  tests  tutorials
```

**The cd command**
```
cd path/to/directory
```
This command lets you move between folders. You can specify any path, copy it from the file explorer or just repeat the command until you get where you need to.

`cd ..` Moves to the parent folder. `cd tutorials` moves to a folder called tutorials in your current folder and so on. If you need to switch to a different drive, you would use `cd C:\path\to\directory` where `C` is the drive. Note that between windows, mac and linux, the paths are slightly different. 

**To-Do**

1. Use the `cd` command in your VS Code terminal to move from the folder `Navigate` to the folder `tutorial_1`

```bash
# Windows Powershell
cd .\tutorials\tutorial_1\

# Linux/MacOS
cd tutorials/tutorial_1/
```

On windows, please use powershell over cmd. It is default, but you can also pick it in the VS Code terminal if you need to.



## Setting up Syntax Highlighting (Optional but recommended)

Syntax highlighting shows keywords in the Navigate language in different colors, so that writing `.nav` and `.inc` files becomes easier.

### VS Code

1. In the left sidebar, click extensions.
2. Still in the sidebar, on the top, click `...`
3. Select *Install from VSIX*
4. Find and select the file under `Navigate/syntax/vscode/navigate-language-x.x.x.vsix`

### PyCharm

1. Navigate to `File` -> `Settings`
2. Go to `Editor` -> `TextMate Bundles`
3. Click the `+`
4. Find and select the folder `Navigate/syntax/pycharm/Navigate.tmbundle` 

## Checklist

- Navigate downloaded and open in VS Code (or an editor of your choice)
- Navigate installed through the terminal (leave the terminal open)
- For your convenience, syntax highlighting set up.

For reference, here is the file structure you should be seeing in your VS Code file explorer.

```
Navigate/
├── README.md
├── assumptions/
├── docs/
│   └── tutorials/          <- the tutorial texts, including this guide
├── navigate/
├── simulations/
├── syntax/
├── tutorials/
│   ├── tutorial_1/
│   │   ├── example_solution/
│   │   ├── includes/
│   │   └── tutorial_1.nav
│   ├── tutorial_2/
│   └── tutorial_3/
├── pyproject.toml
└── ...other files...
```

In `tutorial_X`, you find skeleton `.nav` and `.inc` files to fill in and everything else you might need for the tutorials.

In `example_solution`, you find the relevant solution files for each tutorial. 

