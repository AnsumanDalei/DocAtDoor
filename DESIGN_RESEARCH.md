# Product and UI research notes

Research reviewed on 2026-10-02 before the mobile navigation changes. These references informed general interaction principles only; no wording, branding, layouts, code, or imagery was copied.

- [Kyno Health services](https://www.kynohealth.com/services) separates service categories and asks users to select a city before browsing local options. Its public home page communicates visit fees before booking. DocAtDoor has no confirmed service locations or operations, so its non-doctor categories remain clearly enquiry-only and its doctor profiles show configured area/fees without unsupported coverage promises.
- [KITES Senior Care](https://kitesseniorcare.com/) organizes senior care around continuity and family partnership, with a direct request/contact route. This supports DocAtDoor's use of a persistent follow-up queue for service enquiries; the queue does not imply the service itself is bookable.
- [Homeocare online treatment](https://www.homeocare.in/online-treatment.html) describes a connected patient journey with optional report sharing, clinician follow-up, notifications, and doorstep medicine delivery. DocAtDoor implements only its own home visits and private records; it does not claim teleconsultation or medicine delivery.
- [Practo appointment booking help](https://help.practo.com/practo-search/what-is-practo-instant/) explains that bookable providers expose actual available slots, while providers without booking use a separate contact path. This reinforces the app's distinction between validated doctor slots and enquiry-only service links.
- Recent [Behance clinic app design](https://www.behance.net/gallery/250623061/Medora-Clinic-Healthcare-App-Landing-Page-UI-Design) and [Dribbble patient dashboard concept](https://dribbble.com/shots/27622886-Healthcare-Dashboard-Appointment-App) emphasize a coherent design system, clear information hierarchy, responsive layouts, and consolidated appointments/records. These are general design observations, not product feature evidence.

## Applied direction

The mobile header now gives signed-in patients and doctors a fixed, five-item bottom navigation with role-specific labels and visible focus/current states. Desktop navigation remains available. Patient shortcuts cover Home, Find care, Visits, Records, and Inbox; doctor shortcuts cover Dashboard, Hours, Visits, Reviews, and Inbox. The bar respects device safe-area insets and leaves page-end clearance.
