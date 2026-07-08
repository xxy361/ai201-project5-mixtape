# Mixtape - Submission

## AI Usage

**Instance #1: Rating in models.py**

I asked Claude to explain the main files briefly and it gave me a short description for `models.py`, `app.py`, `routes` directory, and the `services` directory. However, it says: "Ratings are their own table with a `UniqueConstraint(user_id, song_id)`, so a user can rate a song only once." I found this statement very strange so I took a closer look at the code for double checking. In the `Rating` model, the piece of code that this statement is talking about is:
```
__table_args__ = (
        db.UniqueConstraint("user_id", "song_id", name="unique_user_song_rating"),
    )
```
I also asked Claude what does `__table_args__` mean, which it told me that this is SQLAlchemy's way of attaching table-level configuration to a model. This piece of code means that the combination of `user_id` and `song_id` must be unique across the whole table. Its previous statement sounded like an user can only rate a song once, which is misleading. This code actually means that there can only be one rating from one person for one song.

**Instance #2:**


## Codebase Map

**Main Files**

`models.py` defines 7 SQLAlchemy models: `User`, `Tag`, `Song`, `ListeningEvent`, `Rating`, `Playlist`, and `Notification`, as well as 3 association tables (`friendships`, `song_tags`, `playlist_entries`). The `playlist_entries` table is a join table that adds an `position` column — songs in a playlist have an explicit position, not just insertion order. Ratings are their own table with a `UniqueConstraint(user_id, song_id)`, so it is one rating per user per song. 

`app.py` is the application factory. It creates the single database object that every other file imports, loads config, registers the four blueprints under `/songs`, `/playlists`, `/users`, and `/feed`, and initiates the database. 

`seed_data.py` populates the database with sample users, songs, and playlists so the API has data to return during development.

**Routes**

`feed.py` handles the `/feed` endpoints: a friends' listening-now feed and a general activity feed.

`playlists.py` handles the `/playlists` endpoints: create a playlist, get its details, list its songs, and add a song.

`songs.py` handles the `/songs` endpoints: search songs, get a song's details, rate a song, and record a listen.

`users.py` handles the `/users` endpoints: get a user's profile, their listening streak, and their notifications.

**Services**

`feed_service.py` builds the friends' listening-now feed (listens within the last 24 hours, one per friend) and the general activity feed (most recent listens, not time-filtered).

`notification_service.py` handles ratings and notifications: rating a song, adding a song to a playlist, and creating and reading notifications. Adding someone else's song to a playlist sends a notification to that song's sharer.

`playlist_service.py` creates playlists and reads them back, returning their songs in playlist order.

`search_service.py` searches songs by title or artist and fetches a single song by ID.

`streak_service.py` records listening events and updates a user's listening streak, which increments on consecutive days and resets when a day is skipped.

### Data Flow 

**Example: adding a song to a playlist triggers a notification**

User adds a song to a playlist: `POST /playlists/<id>/songs in routes/playlists.py` calls `notification_service.add_to_playlist()`. That function appends the song to the playlist. If the person adding the song isn't the original sharer, that function creates a Notification record for the song's original sharer. The sharer later reads it via `GET /users/<id>/notifications`. There's no "send notification" endpoint; notifications are created as a side effect of adding the song.

### Notable Patterns

- Every route delegates to a service function. Routes only parse input and format the JSON response. All business logic and database access live in `services`.
- Services raise `ValueError` on missing records or bad input, which the routes translate into `404`/`400` responses.
- Every model has a `to_dict()` that defines its JSON shape, so the API's output is decided in `models.py`, not in the routes.
- `db` is one shared object sitting at `app.py`. `models.py` and every service have `from app import db`.


## Bug Fix #1: "My listening streak keeps resetting" (Issue #1)

**Reproduction Steps**

- Before attempting to reproduce the bug, found existing tests under the `test/` folder
- Ran the streak tests under with `pytest tests/test_streaks.py`. The `test_streak_increments_on_sunday` test failed, while the other tests (new user, consecutive weekday, same-day, and skipped-day) all passed
- Looking into the streak test, the test simulates a user listen on consecutive days by calling `update_listening_streak` with `now` advancing one day at a time
- The streak increments normally except in the failed scenario that `now` lands on a Sunday.
- The bug triggers when the user is listening on a Sunday, the streak resets to 1 even though they have had listened on the previous day.

**Navigation Path**

1. Looked at `services/streak_service.py` and read the `update_listening_streak` function
2. Compared the code with the streak rules written in the docstring 
3. The docstring didn't mention any rules about days of a week, but there exists a condition `today.weekday() != 6` that resets the streak
4. This is likely the cause because this rule indicates that streaks are reset on Sundays

**Root Cause**

`services/streak_service.py` (line 73-74)
```
elif days_since_last == 1 and today.weekday() != 6:
    user.listening_streak += 1
```

The `weekday() != 6` clause means that when today is Sunday, a user who listened yesterday failed the condition and fell into to the `else`, resetting the streak to 1 instead of incrementing. 

The docstring says:
  - If the user hasn't listened before: streak starts at 1.
  - If the user already listened today: no change.
  - If the user listened yesterday: streak increments by 1.
  - If more than one day has passed: streak resets to 1.

This `weekday() != 6` condition shouldn't be here since it is never mentioned in the docstring.

**Fix Description** 

- Removed the `and today.weekday() != 6` so the `elif` condition is simply `days_since_last == 1`, matching the streak rules in the docstring

**Side-Effect Check**

- Reran the streaks test (`test_streaks.py`) and confirmed that all the tests passed. These tests covered other edge cases for `update_listening_streak`, which is what the function fixed. Since the tests passed, other branches for the if-else statement still behave correctly and match the streak rules in the docstring.


## Bug Fix #2: "The last song in a playlist never shows up" (Issue #5)

**Reproduction Steps**

- Before attempting to reproduce the bug, found existing tests under the `tests/` folder
- Ran the playlist tests with `pytest tests/test_playlists.py`. The `test_playlist_returns_all_songs` and `test_playlist_returns_songs_in_order` tests failed, while the empty-playlist test passed
- Looking into the tests, the `seed_playlist` fixture builds a playlist with 5 songs ("Track 1" through "Track 5") at positions 1–5, then calls `get_playlist_songs` to read them back
- `test_playlist_returns_all_songs` expected 5 songs but got 4, and `test_playlist_returns_songs_in_order` showed the returned list was missing the final "Track 5"
- The bug triggers when reading back a playlist: the last song (highest position) is consistently dropped, so `get_playlist_songs` returns one fewer song than was added

**Navigation Path**

1. Looked at `services/playlist_service.py`
2. Read the `get_playlist_songs` function. Since only the last song doesn't show up, that means there is no problem creating a playlist, getting a playlist, or getting user's playlist.
3. Read the docstring, which has a note that says "this function returns all songs in the playlist."
4. This function is likely the cause because the last song in a playlist supposes to show up according to the note in the docstring

**Root Cause**

`services/playlist_service.py` (line 66)
```
return [song.to_dict() for song in songs[:-1]]
```

The `songs[:-1]` slices off the last element, so the highest-position song is dropped from the returned results. This makes sense that the tests return 4 tracks and lose the "Track 5".

**Fix Description** 

- Removed the `[:-1]` and kept the return statement as `return [song.to_dict() for song in songs]`, matching the docstring description that the function returns all songs in the playlist.

**Side-Effect Check**

- Reran the playlist tests (`test_playlists.py`) and confirmed that all the tests passed, including `test_empty_playlist_returns_empty_list`. This matters because `[:-1]` on an empty list would have silently returned an empty list too, so removing the slice needed to be verified against the empty-playlist edge case. Since that test still passes, an empty playlist correctly returns `[]` and a populated playlist now returns all its songs in position order.


## Bug Fix #3: "The same song keeps showing up twice in search" (Issue #3)

**Reproduction Steps**

**Navigation Path**

**Root Cause**

**Fix Description** 

**Side-Effect Check**


## Commit History
<!-->
Run git log --oneline on your bugfix/mixtape branch. Take a screenshot.
<-->

