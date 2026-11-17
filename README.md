# C.A.T.E.R.

**Catering Asset Tracking and Equipment Retrieval** — tracks a catering business's
equipment, which event it is out on, who is working it, and whether it came back.

1. In phpMyAdmin, create an **empty** database, for example `cater_db`. Do not create tables.

2. Install the packages:
   ```
   python -m venv venv
   venv\Scripts\activate         
   pip install -r requirements.txt
   ```

3. Copy `.env` and fill it in:
   ```
   SECRET_KEY=any-long-random-text
   DATABASE_URL=mysql+pymysql://root:@localhost/cater_db
   MAIL_USERNAME=youraddress@gmail.com
   MAIL_PASSWORD=your-gmail-app-password
   ```

4. Start it, then open http://127.0.0.1:5000:
   ```
   python run.py
   ```

## Good to know

- **The database sets itself up.** The tables are created the first time the app starts.
  There is nothing to import.
- **The first account you register becomes the admin.** Everyone after that is staff.
  To promote someone later: `UPDATE user SET role='admin' WHERE email='their@email.com';`
- **Admins vs staff.** Both can view everything, add and edit equipment and events, and
  record packing and returns. Only admins can delete things and put staff on an event.
- **SMTP works using Gmail**, changing email and password reset needs verification.

## Client engagement

| | |
| --- | --- |
| **Client** | Casa Padrid Catering Services |
| **Interview** | Face to Face interview with one of the staff involved in logistics |
| **Requirements** | Equipments registration, Events list, Checklists, Easy to search equipments, satff names, and events, Logs of equipment assigning and retrieval with filtering |
