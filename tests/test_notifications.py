"""
tests/test_notifications.py — Mixtape

Tests for notification generation when friends interact with shared songs.
"""

import pytest
from app import create_app, db
from models import User, Song
from services.notification_service import rate_song, get_notifications
from services.playlist_service import create_playlist


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def seed(app):
    """Create a sharer, a friend, a song shared by the sharer, and a playlist."""
    with app.app_context():
        sharer = User(username="sharer", email="sharer@example.com")
        friend = User(username="friend", email="friend@example.com")
        db.session.add_all([sharer, friend])
        db.session.flush()

        song = Song(title="Shared Track", artist="Various", shared_by=sharer.id)
        db.session.add(song)
        db.session.flush()

        playlist = create_playlist(name="Friend's Playlist", created_by_user_id=friend.id)

        db.session.commit()
        yield {
            "sharer_id": sharer.id,
            "friend_id": friend.id,
            "song_id": song.id,
            "playlist_id": playlist.id,
        }


def test_notifies_sharer_when_song_rated(app, seed):
    """Rating a friend's song should notify the sharer (currently fails: bug #4)."""
    with app.app_context():
        rate_song(seed["friend_id"], seed["song_id"], 5)
        notifs = get_notifications(seed["sharer_id"])
        assert len(notifs) == 1
        assert notifs[0]["type"] == "song_rated"


def test_no_self_notification_when_rating_own_song(app, seed):
    """Rating your own song should not create a notification."""
    with app.app_context():
        rate_song(seed["sharer_id"], seed["song_id"], 4)
        notifs = get_notifications(seed["sharer_id"])
        assert notifs == []
