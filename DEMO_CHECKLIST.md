# RideFlow demo checklist

## Start and check

Run these commands from the project folder:

```bash
source venv/bin/activate
python manage.py migrate
python manage.py check
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Use two browser profiles or one normal and one private window to keep customer and staff sessions separate. Have an internet connection for Bootstrap styling. Existing sample customers are `customer1` through `customer5`, password `DemoPass123!`. Customers sign in at `/accounts/login/`; sign in as staff with your own staff/superuser account at `/admin/login/?next=/dashboard/staff/`.

## Walk through a rental

1. Browse the homepage and fleet. Search for a vehicle, apply a price/category filter and move between result pages. The filters stay selected.
2. Register a customer and show that they are immediately signed in and land on My rentals. Save a car from the catalogue, show it under Saved cars and on the dashboard, then remove it if desired. Open My profile to show contact details and password management. Returning customers can sign in with their existing account.
3. Choose a vehicle with no conflicting reservation. Create a booking with pickup today and return tomorrow so you can demonstrate an early return today. Note the reference and server-calculated total.
4. Try the same dates on the same vehicle from another customer account. The form should explain the conflict without creating another booking.
5. In the staff session, open Bookings and move the rental through Confirmed, Ready for pickup and Active.
6. Record a cash or bank-transfer payment. Select Paid for a confirmed receipt, or Partial for an installment already received. Use a unique reference. This records a manual receipt; no money is transferred by the application.
7. In the customer session, open the booking to show payment history and the updated outstanding balance.
8. In the staff session, choose Process return. Use today's date, add condition notes and optionally an additional fee. Only mark damage if you want the vehicle to be held as Damaged.
9. Show the return summary and updated balance. Record any remaining payment, then mark the booking Completed.
10. Verify the staff dashboard and fleet status. An undamaged vehicle becomes Available unless it has another confirmed reservation.
11. Submit the contact form. In `/admin/`, open Core → Contact messages to show the saved inquiry and mark it resolved.

Cancellation is available before activation. Cancelling one reservation does not release a vehicle that is still rented on another booking. Refunds remain a manual staff process.

## Before handing in

Run `python manage.py test` and `python manage.py makemigrations --check --dry-run`. Capture the screens required by your institution and add your name, student ID, department and institution to your report. Use `DEFENSE_GUIDE.md` to rehearse the architecture, overlap rule, roles and limitations.

Keep a backup of your local database and uploads before moving machines. Recreate the virtual environment from `requirements.txt` on the destination machine; do not copy `venv`. Share only demonstration data, and exclude real customer data and license documents from a submission or public repository.
