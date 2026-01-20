# Dont put this in your apps directory in deimos **IT WILL SOFT BRICK YOUR PICO**
# this is intended to be ran on a host device

# How to use
1. find a gif
2. run `encode.py <your gif>`
3. run `mpremote mount . run playgif.py`


This plays GIFs at a decent FPS, as I am  not clearing the screen every frame.
I am instead doing delta updates.
Also this uses the 4 shades the Casio CWII supports.

Join the discord for more info on deimos
https://discord.gg/HxjSzJjb37

## this code was fully vibe coded, so there is probably alot that can be improved on. I do not claim to be good at coding.

# TODO
add keyboard interupt handling
