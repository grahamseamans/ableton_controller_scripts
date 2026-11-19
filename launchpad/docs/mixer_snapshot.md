the goal of this controller is to:

using the launchpad
have the grid

and one super button - i dont care whcih, just not a grid button, we can change this alater

if you hit a grid button with super: it snapshots the mixer state (really just volume for now is sufficient)
if you hit that grid button later: it recalls that mixer state


each row gets a different color
after you recall a mixer state that button should be brighter than th eothers, if you change a parameter the light should go donw to notmal, as it's no longer selected.
if there is no snapshot on a grid button it is off
the state with the snapshots is somehow saved within the project so that it will work when opened later

next steps for later:
- more of the mixer than just volume
- capture what clips are playing in each track