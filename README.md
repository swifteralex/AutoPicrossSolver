# AutoPicrossSolver
A program that automatically solves Picross Touch levels with the press of one key.

https://user-images.githubusercontent.com/54672346/123477130-77754080-d5b2-11eb-8ef1-34aacaa10cae.mp4

## Installation

This project uses Python 3.7.6, with the following packages and their respective versions installed:

```
pip install opencv-python==4.2.0.32

pip install tensorflow==2.12.0

pip install h5py==2.10.0

pip install PyAutoGUI==0.9.52

pip install pynput==1.7.3

pip install picross-solver==1.1.2
```

Other versions of Python and each package might work, but they haven't been tested.

## How to Use

Once the libraries are installed, clone this repo and simply run the main.py file to start the solver (ex. `python main.py`). The program will then take a few seconds to load all of the necessary files. Once completed, navigate to Picross Touch and open an empty puzzle for the solver to work on. Make sure Picross Touch is in full-screen and that the current Picross Touch theme is one made in only the Simple Editor; other themes may work, but they aren't guarenteed. Press 'Enter' to start the solver. Depending on the puzzle, the solver will take at most a couple seconds before it starts automatically filling in the puzzle by taking over the mouse. Moving the mouse will stop the solver while it's filling in the puzzle. Press 'Esc' to close the program while it's not currently solving a puzzle.

At the top of main.py, the start and exit keys can be changed by the user if they prefer to use keys other than 'Enter' and 'Esc'. The clicking speed of the solver can also be changed.
