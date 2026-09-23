# Project Defense Guide

## Project overview

RideFlow addresses fragmented, manual vehicle-rental operations. Its aim is to design and implement a web system that gives customers a secure reservation experience and staff a centralized fleet workflow. The scope covers accounts, profiles, fleet browsing, date-based booking, manual payment records, vehicle returns, stored contact inquiries, dashboards and administration. Live gateways, GPS, multiple branches and notifications remain future work.

Functional requirements include authentication, vehicle discovery, booking validation, pricing, lifecycle management, payments and returns. Non-functional requirements include security, responsiveness, maintainability, reliability and usability.

## Architecture and database

Django follows Model–View–Template. Models define data and business constraints; views authorize requests and coordinate workflows; templates render HTML. URL configurations route requests. Forms validate user input, middleware provides sessions/authentication/CSRF protection, and the ORM translates QuerySets into SQL.

The apps are separated by business responsibility. `User — CustomerProfile` is one-to-one because each customer needs one extended profile. `VehicleCategory — Vehicle`, `User — Booking`, `Vehicle — Booking`, and `Booking — Payment` are one-to-many ForeignKey relationships. `Booking — VehicleReturn` is one-to-one because a rental is returned once. `PROTECT` preserves financial and rental history.

## Booking algorithm

The server rejects past pickup dates, return dates that are not later, inactive or operationally unavailable vehicles, and overlapping active bookings. Two date ranges overlap when `existing.pickup < new.return` and `existing.return > new.pickup`. This intentionally permits a new pickup on an earlier booking's return date. The creation view uses a database transaction and locks the selected vehicle row where supported, then the model validates again before saving. Duration is `return - pickup`; rental amount is duration multiplied by the vehicle's database price, and total adds the database security deposit. No client-submitted price is trusted.

Booking states follow `PENDING → CONFIRMED → READY_FOR_PICKUP → ACTIVE → RETURNED → COMPLETED`, with defined rejection/cancellation branches. A centralized transition map rejects invalid jumps and synchronizes fleet status from all live rentals/reservations. Status changes use the latest booking record inside a transaction; they do not revalidate an old pickup date as a new reservation or recalculate the agreed price. The return record and status change are saved together, and a damaged vehicle stays out of service. Direct admin status changes are disabled; staff use the booking workflow.

## Security and demonstration

Security includes Django password hashing and sessions, CSRF tokens, server-side forms, login and staff decorators, object-filtered customer booking/payment queries, POST-only cancellation/deactivation, upload handling, messages, and production-friendly error pages. In the demonstration: browse and filter; register; reserve a vehicle; show the computed price and dashboard; attempt a conflicting booking; sign in as staff; confirm it; record payment; activate it; process return; complete it; then show revenue and fleet statistics.

## Challenges, solutions, limitations

The key challenge is consistency between availability, booking status and vehicle status. It is handled through reusable model validation, database transactions and centralized transitions. Money uses `DecimalField` to avoid binary floating-point errors. The MVP uses SQLite and simulated payments; commercial deployment should use PostgreSQL, a payment provider, background jobs, audit logs, stronger concurrency tests and cloud media storage.

## Likely questions and answers

1. **Why Django?** It provides authentication, ORM, forms, CSRF protection, admin and a mature project structure, allowing secure delivery without reinventing core services.
2. **Why SQLite?** It requires no server and is ideal for development and demonstration. The ORM makes later PostgreSQL migration straightforward.
3. **What is Django ORM?** It maps Python model operations to SQL while providing expressive, parameterized database queries.
4. **Explain MVT.** Model manages data, View handles request logic, and Template renders presentation.
5. **What is a ForeignKey?** A many-to-one relationship; many bookings can reference one vehicle.
6. **What is OneToOneField?** A relationship allowing exactly one related row, used for the extended customer profile and rental return.
7. **How is double booking prevented?** The model queries active bookings for overlapping date intervals and creation runs inside a transaction with a vehicle-row lock where supported.
8. **Why are comparisons strict?** Strict `<` and `>` allow one rental to start on the exact day another ends.
9. **How do you prevent unauthorized access?** Login/staff decorators protect views, and customer detail queries are filtered by the current user.
10. **What if a customer changes a booking URL?** A booking outside that customer's queryset returns 404, revealing no private record.
11. **What if two customers book simultaneously?** The transaction serializes access to the vehicle row on databases supporting row locks; validation occurs after the lock. PostgreSQL is recommended for production concurrency.
12. **Why server-side price calculation?** Browser values can be altered, so trusted vehicle prices and dates are read from the database.
13. **Why DecimalField for money?** Decimal arithmetic represents currency precisely; binary floats can introduce rounding errors.
14. **How does authentication work?** Django hashes passwords, creates a server-side session after login and associates requests with the authenticated user.
15. **What is CSRF?** Cross-Site Request Forgery tricks a browser into submitting an unwanted action. Django tokens verify that POSTs originate from the application.
16. **What is a migration?** A versioned description of database-schema changes that Django applies consistently.
17. **What is middleware?** Request/response processing around views; this project uses it for security, sessions, authentication, CSRF and messages.
18. **What is a QuerySet?** A lazy, composable representation of a database query.
19. **Why use ModelForms?** They connect model fields and validation to HTML forms while reducing duplicated code.
20. **Why separate apps?** Each app owns a cohesive business area, improving readability, testing and maintenance.
21. **Why use `PROTECT`?** Rental, payment and return history should not disappear if someone tries to delete a referenced record.
22. **How are statuses controlled?** A single transition map defines the legal next states; random state changes raise validation errors.
23. **How is vehicle availability represented?** Operational status describes the fleet condition while booking overlap queries determine availability for dates.
24. **How are late returns handled?** The return stores expected and actual dates; late days are the positive difference, and staff enter the MVP fee.
25. **How is outstanding balance calculated?** Original booking total plus recorded return fees, minus received Paid and Partial records, never below zero. Cancelled/rejected bookings have no rental balance; refunds and deposit reconciliation are manual.
26. **How is the UI responsive?** Bootstrap grids/tables/navbar and targeted CSS media rules adapt pages for desktop, tablet and mobile.
27. **What does `select_related` do?** It joins ForeignKey data into one query to avoid repeated database queries.
28. **What tests are most important?** Invalid dates, overlaps, backend price calculation, authorization and status permissions because failures affect money, privacy or inventory.
29. **What is the admin site's role?** It provides administrators with audited model management, while custom staff pages support the daily rental workflow.
30. **How would you commercialize it?** Move to PostgreSQL, environment-based secrets, HTTPS, object storage, a gateway, email/SMS jobs, audit logs, monitoring and deployment automation.
31. **What is pagination?** It splits large query results into manageable pages, improving response time and usability.
32. **Why not React?** Django templates satisfy the MVP's interactions with less complexity and make the system easier to explain and maintain.
33. **What does `full_clean()` do?** It runs field and model validation before the booking is persisted.
34. **What is the main limitation?** SQLite has limited concurrent-write behavior and payments are simulated; neither is appropriate for a high-volume commercial launch.
35. **What did you learn?** How to translate operational rules into database relationships, validation, authorization, transactions, reusable workflows and tests.
