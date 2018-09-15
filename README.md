# Tipresias

I Tipresias, old bot with dusty boards<br>
Perceived the match, and foretold the score—<br>
I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim his throne as the master of AFL footy tipping models.

## Run Jupyter in Docker
* Build docker image with `docker build ./ -t tipresias:latest` (use a different `name:tag` if you prefer)
* Run Jupyter with `docker run -it -p 8888:8888 tipresias:latest jupyter notebook --ip 0.0.0.0 --no-browser --allow-root`, then copy/paste the URL given.