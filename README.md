# RideFlow Vehicle Rental and Fleet Management System

A Django demonstration project for customers to browse vehicles, make conflict-checked reservations, follow rentals, and see payment balances. Staff manage fleet records, customers, booking lifecycles, manual payments, returns, and business summaries from a separate dashboard.

## Problem statement and objectives

Manual rental records make availability difficult to verify and can cause double bookings, inaccurate charges, and poor visibility. RideFlow centralizes the process. Its objectives are to provide online vehicle discovery and reservations, enforce booking and pricing rules on the server, protect customer data, and provide staff with a clear operational dashboard.

## Features

- Customer registration, authentication, profile and password management
- Matching signup/login layouts with inline validation, password visibility controls and autofill support
- Responsive public site, vehicle catalogue, search, filters and pagination
- Server-calculated prices and date-overlap prevention
- Customer booking history, detail, cancellation and payment balances
- Automatic sign-in after registration and a dedicated My rentals dashboard
- Private saved-car shortlists, with save/remove controls throughout the catalogue
- Customer cart combining saved cars and pending bookings, with a navigation count and WhatsApp payment links
- Staff fleet, booking, customer, payment and vehicle-return workflows
- Controlled booking status transitions and role/object-level authorization
- Private license-document downloads for the owner and staff
- Validated contact messages stored for review in Django admin
- Customized Django admin, sample data command, friendly error pages and tests

## Technology

Python 3, Django 6.1, Django Templates, SQLite, Bootstrap 5, CSS, vanilla JavaScript and Pillow. Django ORM keeps the data layer portable to PostgreSQL.

## Requirements and installation

Python 3.12+ and pip are recommended.

```bash
python3 -m venv venv
source venv/bin/activate              # macOS/Linux
# venv\Scripts\activate              # Windows Command Prompt
# venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data
python manage.py runserver
```

On systems where Python is named `python3`, use `python3 manage.py ...`.

Sample customers are `customer1` through `customer5`; their development password is `DemoPass123!`.

### Start this existing copy

From the project folder on macOS/Linux:

```bash
source venv/bin/activate
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Keep the terminal open while using the site; press Ctrl+C to stop it. You can also run `venv/bin/python manage.py runserver` without activating the environment. Use your own superuser account for the staff dashboard and `/admin/`; create one with `python manage.py createsuperuser` if needed. Do not rerun `seed_data` unless you want sample records.

Bootstrap CSS and JavaScript are loaded from a CDN, so the demo needs an internet connection for its Bootstrap styling and mobile menu. Vehicle images and the custom stylesheet are local. Sample data can be loaded again without duplicating its named demo bookings; it does not refresh old bookings into the future. Create a new booking for a current demonstration.

## Project structure

```text
vehicle_rental/  settings and root URLs
accounts/        registration and customer profiles
vehicles/        categories, fleet catalogue and staff vehicle management
bookings/        availability, pricing, lifecycle and vehicle returns
payments/        manual payment records and balances
dashboard/       customer and staff summaries
core/            public pages and error handlers
templates/       reusable Django templates and partials
static/          site CSS and JavaScript
```

## Roles

- Visitor: browses cars, prices and details without creating an account.
- Customer: books cars, manages their own rentals, saves favourites and updates their profile. Their dashboard contains no fleet/customer/payment administration tools.
- Staff: manages fleet operations, all bookings, payments, customers and returns.
- Administrator: full staff features plus Django admin and user/permission management.

## Data relationships

`User` has one `CustomerProfile`. A `VehicleCategory` has many `Vehicle` records. A user and a vehicle each have many `Booking` records. A booking has many `Payment` records and at most one `VehicleReturn`. `PROTECT` is used for operational history so referenced rentals cannot be accidentally deleted.

`SavedVehicle` links a customer to a favourite car, with a unique customer/car constraint. Saved cars are private bookmarks; they do not hold availability or create bookings.

## Rental and payment rules

Successful checkout automatically opens a WhatsApp chat with `+2347081724880`, with the reference, car, dates and outstanding amount prefilled. The customer sends the message to arrange payment; this is not an online payment gateway. A Pay via WhatsApp button remains on unpaid booking details, and returning to the booking does not repeatedly redirect. Staff still verify the payment and record it through the existing payment workflow. Set `WHATSAPP_PAYMENT_NUMBER` to change the recipient (international format, digits only).

- Rental dates use a return-exclusive interval: pickup on another booking's return date is allowed.
- Prices and deposits are calculated when a booking is created and stay fixed even if fleet prices change later. To change dates or vehicle, cancel the booking and create another.
- Staff use Bookings to move a rental through Pending → Confirmed → Ready for pickup → Active → Returned → Completed. The Process return page is required to record a return. Staff can also mark an active rental Overdue; this is currently a manual action.
- Fleet status considers all active rentals and confirmed reservations. A damaged return stays Damaged until staff clear it after inspection or repair.
- Return fees are entered by staff and added to the original booking amount. Actual returns cannot be before pickup or in the future.
- Paid and Partial payment records both represent money received and reduce the balance. Pending, Failed and Refunded records do not. Use a unique transaction reference for each record and the Django admin to correct its status when necessary.
- Cancellation/rejection removes the rental balance. Payments and deposit refunds are handled manually; there is no live payment gateway or automatic refund. The staff payment total is money received, including deposits, rather than an accounting profit report.
- Contact messages are stored under **Core → Contact messages** in Django admin. They are not emailed automatically.

## Signup and login

First and last names are required at signup, including server-side validation for blank or whitespace-only values.

Customer sign-in is at `/accounts/login/`. Staff and administrators use the separate operations sign-in at `/admin/login/`; customer credentials cannot sign in there, and staff are directed to that page if they try customer sign-in. Staff links retain their intended destination after login. Staff accounts are created by an administrator, not through public signup.

Signup checks username and email availability, password strength and password confirmation on the server. Passwords are hashed through Django, and the account and customer profile are saved in one transaction. Successful registration signs the customer in and opens My rentals immediately. Returning customers sign in with their username and password; an email address is not a login name.

Login resolves username capitalization using the same database matching rule as signup, while passwords remain exact and case-sensitive. Incorrect passwords and inactive accounts are rejected. Both forms show validation errors beside the relevant fields, and password fields have Show/Hide controls and a Caps Lock hint.

Visitors can browse freely. Booking and saving require an account. If someone starts signup from a selected car, the dashboard offers a link to continue with that car. Existing customers signing in to book return to their chosen booking page. The customer dashboard prioritizes the current rental or next booking, saved cars, booking history and profile details; staff keep their separate operations dashboard. See [CUSTOMER_EXPERIENCE.md](CUSTOMER_EXPERIENCE.md) for the MVP design brief.

## Car showcase

Visit `/vehicles/showcase/` (Showcase in the customer/public navigation) for animated car cards, daily prices, brand/year filters and price sorting. Save keeps a private shortlist; Add to cart saves the car and opens the cart. Dates and a booking are still required before checkout; neither action reserves a vehicle.

Run `python manage.py seed_showcase` to add the expanded demonstration catalogue spanning 2006–2026. It is repeatable and preserves existing listings and edited rates. Added listings are explicitly labelled as demos: prices and configurations are illustrative, and cars without photos use labelled illustrations. Replace these with verified fleet details, rental rates and your own photos before public launch.

Generated car illustrations live in `media/vehicles/ai-showcase/`. Run `python manage.py attach_showcase_images` after seeding to attach available images without replacing existing uploaded photos. See [AI_CAR_IMAGES.md](AI_CAR_IMAGES.md) for generation prompts and limitations.

## Running tests

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

The tests cover automatic signup login, returning-user login, customer dashboards, private saved cars, password validation, username matching, redirect safety, private documents, catalogue validation and pagination, contact persistence, pricing, overlaps, historical bookings, fleet consistency, atomic returns, payment balances, authorization, repeatable sample data and a complete rental/payment workflow. Tests use a separate test database.

## Demonstration and submission

Follow [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) for the presentation flow and [DEFENSE_GUIDE.md](DEFENSE_GUIDE.md) for architecture and viva questions. If your submission requires screenshots, capture the homepage, filtered catalogue, booking details, customer dashboard, staff dashboard and completed return. Add your author/student details to the submitted report.

## Configuration and deployment limits

The included setup is for local demonstrations, using SQLite and manual payment records. `.env.example` documents the environment variables; it is not loaded automatically. `DJANGO_DEBUG=False` requires a separate `DJANGO_SECRET_KEY` and enables HTTPS-only settings. Supply an explicit `DJANGO_ALLOWED_HOSTS` value for a deployment.

A public launch still needs a deployment target, PostgreSQL and concurrency verification, a production application server, static/media hosting, backups, monitoring, and operational payment/refund policies. Keep `/media/licenses/` routed through the authenticated Django download view; never expose that directory through a public media server. Do not publish the local database, demo credentials, uploaded license documents or private customer data. The ignore file excludes these local/private artifacts.

## Future improvements

PostgreSQL deployment, Paystack/Stripe, notifications, multiple branches, inspections, maintenance reminders, PDF receipts, REST API, advanced reporting and real-time inventory coordination.
