# Tipresias

I Tipresias, old bot with dusty cores<br>
Perceived the match, and foretold the score—<br>
I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim its throne as the master of AFL footy tipping models.

## Running things

### Run the app

- `docker-compose up` (add `--build` to build the images)
- Navigate to `localhost:3000`.

### Run Jupyter notebook in Docker

- If it's not already running, run Jupyter with `docker-compose up notebook`.
- The terminal will display something like the following message:

```
notebook_1  | [I 03:01:38.909 NotebookApp] The Jupyter Notebook is running at:
notebook_1  | [I 03:01:38.909 NotebookApp] http://(ea7b71b85805 or 127.0.0.1):8888/?token=**dhf7674ururrtuuf8968lhhjdrfjghicty57t69t85e6dhfj**
notebook_1  | [I 03:01:38.909 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
```

- Copy the URL given and paste it into your browser.
- Alternatively, copy just the token (bolded above) from the terminal, navigate your browser to `http://localhost:8888`, and paste the token into the given field.

### Run Python tests

- `docker-compose run server pytest`
