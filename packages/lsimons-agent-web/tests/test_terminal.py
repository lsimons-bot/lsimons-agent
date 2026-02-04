"""Tests for terminal module."""

import time

from lsimons_agent_web.terminal import Terminal


def test_terminal_start_stop():
    """Test starting and stopping a terminal."""
    term = Terminal(shell="/bin/sh")
    assert not term.is_running()

    term.start()
    assert term.is_running()
    assert term.pid is not None
    assert term.master_fd is not None

    term.stop()
    assert not term.is_running()
    assert term.pid is None
    assert term.master_fd is None


def test_terminal_write_read():
    """Test writing to and reading from terminal."""
    term = Terminal(shell="/bin/sh")
    term.start()

    try:
        # Write a command
        term.write(b"echo hello\n")

        # Wait for output
        time.sleep(0.2)

        # Read output
        output = b""
        while True:
            data = term.read_nowait()
            if data is None:
                break
            output += data

        # Should contain our command output
        assert b"hello" in output
    finally:
        term.stop()


def test_terminal_resize():
    """Test resizing the terminal."""
    term = Terminal(shell="/bin/sh")
    term.start()

    try:
        # Resize should not raise
        term.resize(40, 120)
    finally:
        term.stop()


def test_terminal_start_idempotent():
    """Test that calling start twice doesn't spawn a second process."""
    term = Terminal(shell="/bin/sh")
    term.start()
    pid1 = term.pid

    term.start()  # Second call should be no-op
    pid2 = term.pid

    assert pid1 == pid2
    term.stop()


def test_terminal_stop_idempotent():
    """Test that stop can be called multiple times safely."""
    term = Terminal(shell="/bin/sh")
    term.start()
    term.stop()
    term.stop()  # Should not raise
    assert not term.is_running()


def test_terminal_scrollback():
    """Test that scrollback buffer captures output."""
    term = Terminal(shell="/bin/sh")
    term.start()

    try:
        # Write a command
        term.write(b"echo hello\n")

        # Wait for output
        time.sleep(0.2)

        # Drain the queue
        while term.read_nowait() is not None:
            pass

        # Scrollback should contain output
        scrollback = term.get_scrollback()
        assert b"hello" in scrollback
    finally:
        term.stop()
