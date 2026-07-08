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
<!-->
1. Issue number and title
2. How you reproduced it — What steps did you take to confirm the bug exists before touching any code? What inputs, sequence of actions, or data condition triggered the behavior?
3. How you found the root cause — Which files did you look at? What was your navigation path? What moment made you confident you'd found the right place — not just a suspicious area, but the specific cause?
4. The root cause — In plain English, explain exactly what was wrong. Not "there was a bug in the streak logic" — explain the specific condition, comparison, or missing step that caused the problem.
5. Your fix and side-effect check — What did you change and why does that change fix the root cause? What related functionality did you check afterward to confirm you didn't break anything?
<-->


## Commit History
<!-->
Run git log --oneline on your bugfix/mixtape branch. Take a screenshot. Confirm there is one commit per bug fix with a meaningful fix: message. If multiple fixes are bundled in one commit, it's worth separating them now before submitting.
<-->

