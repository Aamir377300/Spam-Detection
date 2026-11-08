# To be continued

The Gmail check is the feature still left to finish.

The page already has a **Run** button for `auselessbuddy25@gmail.com`. Pressing it is supposed to open that inbox, read the five newest messages, and label each one spam or not spam. That live login has not been completed. Gmail refused to use the normal account password, and `.env` does not have an app password yet.

## What is already in the code

- The account on the page is `auselessbuddy25@gmail.com`.
- **Run** calls `POST /api/inbox/run`.
- The server connects to Gmail over IMAP only when Run is pressed.
- It reads the five newest messages in the inbox and scores each one with the same checker as the rest of the app.
- It does not mark those messages as read.
- The results stay on the page. Closing the page clears them. They are not written to a file or to browser storage.
- `.env.example` shows where the password goes. `.env` is ignored by git.

Until the password is added, Run stops with: add `GMAIL_APP_PASSWORD` to `.env` and restart the app.

## What still has to be done

1. Turn on 2-Step Verification for `auselessbuddy25@gmail.com`.
2. Open https://myaccount.google.com/apppasswords and create a Mail app password.
3. Put that 16-character password in `.env`:

   ```
   GMAIL_ADDRESS=auselessbuddy25@gmail.com
   GMAIL_APP_PASSWORD=the-app-password
   ```

4. Restart the app from this folder:

   ```bash
   source .venv/bin/activate
   python -m app
   ```

5. Open http://127.0.0.1:8000 and press **Run**.
6. Confirm the five newest inbox messages appear, each with a spam or normal label, and that closing the page removes them.

Do not put the normal Gmail password in `.env` or in the chat. The app password is the only password this feature should use.
