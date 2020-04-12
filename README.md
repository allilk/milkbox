# literate-disco
A file UI alternative to Google Drive.
Live Site: https://site.developer.lgbt
(Currently running v0.2 and pending approval by Google.)
If there are any issues in browsing the site, or running your own, I urge you to open a issue on GitHub so I can get it fixed ASAP.

To Do:
- Restful API & ReactJS Implementation
- Complete Context Menu
- Switching between Dark and Light Themes
- Settings panel(to tweak experience)
- Implement a experimental search(searching API rather than cache)
- Finish Changes UI
- Implement sharing
- Fix redirects, implement error pages.

In The Future:
- Allow for other services, like MEGA.
- Higher Authentication for more features like deleting, copying, etc.
- JS Rewrite

List to be updated in the future.


How do I run my own?
- Install and setup PostgreSQL 12, then create a database named "django-ui".
- Follow the first two steps of https://developers.google.com/drive/api/v3/quickstart/python
- `pip install -r requirements.txt `
- Copy and paste https://pastebin.com/EPDhBUBh into `files/config.py`, fill in as needed. 
- Change neccessary settings in `djui/settings.py`.
- `python manage.py migrate`
- `python manage.py runserver`

And ta dah!

Production instructions vary depending on what you choose to use to run the webserver.

Enjoy.

Alli
