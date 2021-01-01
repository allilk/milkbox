# Deprecated, look into: 
https://github.com/allilk/milkbox-svelte

# milkbox
A file UI alternative to Google Drive.


To Do:
- ~~Restful API & ReactJS Implementation~~ Seperate project: https://github.com/allilk/milkbox-js
- Complete Context Menu
- Switching between Dark and Light Themes
- Settings panel(to tweak experience)
- Implement a experimental search(searching API rather than cache)
- Finish Changes UI
- Implement sharing
- Fix redirects, implement error pages.
- ~~Clean up project folder structure~~

In The Future:
- Allow for other services, like MEGA.
- Higher Authentication for more features like deleting, copying, etc.

List to be updated in the future.


How do I run my own?
- Install and setup PostgreSQL 12, then create a database named "django-ui".
- Follow the first two steps of https://developers.google.com/drive/api/v3/quickstart/python
- `pip install -r requirements.txt `
- Copy and paste https://pastebin.com/EPDhBUBh into `files/config.py`, fill in as needed. 
- Change neccessary settings in `backend/settings.py`.
- `python manage.py migrate`
- `python manage.py runserver`

And ta dah!

Production instructions vary depending on what you choose to use to run the webserver.

Enjoy.

Alli
