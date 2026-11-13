# CMS Editors Guide

This guide is intended for **editors and content managers** who use the CMS to review
and organize ZIM files for the Kiwix library. It explains the core concepts of the CMS
and how to perform common tasks through the web interface.

If you are looking for how to install, configure and deploy the CMS, read the
[INTEGRATORS_GUIDE.md](INTEGRATORS_GUIDE.md) instead.

## Table of Contents

- [What is the CMS?](#what-is-the-cms)
- [Core Concepts](#core-concepts)
  - [Books](#books)
  - [Titles](#titles)
  - [Flavours](#flavours)
  - [Collections](#collections)
  - [Warehouses](#warehouses)
  - [Applications](#applications)
  - [App Builds](#app-builds)
  - [Download Statistics](#download-statistics)
  - [Zimfarm Notifications](#zimfarm-notifications)
  - [Events](#events)
  - [Title Uploads](#title-uploads)
- [The Lifecycle of a Book](#the-lifecycle-of-a-book)
- [Roles & Permissions](#roles--permissions)
- [Using the UI](#using-the-ui)
  - [Inbox](#inbox)
  - [Titles](#titles-1)
  - [Books](#books-1)
  - [Collections](#collections-1)
  - [Apps](#apps)
  - [Users](#users)

## What is the CMS?

The CMS is the component of the Kiwix stack that catalogs the ZIM files produced by the
[zimfarm](https://github.com/openzim/zimfarm). It receives a notification every time a
new ZIM is produced, checks that the ZIM meets openZIM's requirements, and
associates it with a **title** (a series of related ZIM files) placed in one or more
**collections** (the catalogs exposed to Kiwix readers).

It is also the place where branded applications for Android and Apple are configured
and from which their builds are triggered.

The web interface is available at [cms.openzim.org](https://cms.openzim.org/).

## Core Concepts

### Books

A **book** is a single ZIM file. It carries the technical metadata of the ZIM
(article count, media count, file size, ZIM metadata such as `Name`, `Title`,
`Creator`, `Language`, …), a `flavour`, and, once processed, a `filename`.

A book always has a **location kind**, which tells you where it currently lives in the
workflow:

- **`quarantine`**: the book has just arrived and has not been validated/attached to a
  title yet. These books appear in the _Inbox_.
- **`staging`**: the book is attached to a title but is not yet ready to be published
  (e.g. the title has manual review enabled, or the book has issues).
- **`prod`**: the book is published. A book is published automatically if manual review
  is disabled for its title and flavour, and it has no issues. If automatic movement to
  `prod` fails because of book issues, an editor has to manually move the book and
  resolve any fixable issues along the way.
- **`to_delete`**: the book has been scheduled for deletion.
- **`deleted`**: the book's files have been removed.

Books can also carry **issues**, which describe problems that prevent a book from being
promoted to `prod`. Common issues include missing mandatory metadata, unsupported
languages, unexpected article/media count changes, recipe mismatches, or zimcheck
errors.

When a book is moved to `staging` or `prod`, it goes through a short **transition**.
The book is immediately shown with its destination location kind, but its download and
view links are not advertised yet. The transition advances as the files are physically
moved, then as the book becomes available on mirrors, and finally as it becomes live in
the library. A book still in transition carries a `transition_status` value
(`moving_files`, `checking_mirrors`, or `checking_library`).

### Titles

A **title** is the logical grouping of all the books that represent the same content
across flavours and across time. For example, the `wikipedia_en_all` title groups every
English Wikipedia ZIM, whatever its flavour or version.

A title has:

- a unique **name** (e.g. `wikipedia_en_all`, `gutenberg_fr_all`)
- the ZIM metadata used to describe the content: `title`, `creator`, `publisher`,
  `description`, `language`, `illustration`, `long_description`, `license`,
  `relation`, `source`
- a **manual review** flag (`yes` or `no`). Books belonging to titles with manual
  review disabled are moved to `prod` automatically when they have no issues; books
  belonging to titles with manual review enabled are always moved to `staging`. This is
  typically `yes` for community titles and `no` for Kiwix titles.
- a **popularity** score (1 to 100), derived from recent download statistics.
    It is used to sort titles in the UI.
- an **archived** flag. Archiving is the equivalent of deleting a title while keeping
  its history.
- one or more **flavours** and **collections**.

### Flavours

A **flavour** is a variant of a title. For example, a title may have a `nopic` (no
pictures) flavour, a `maxi` flavour, a `mini` flavour, and so on. Each flavour is
linked to the zimfarm **recipe** that produces it.

The CMS uses the flavour of a book to decide which recipe a new book belongs to and to
detect problems such as a book arriving with a flavour that is not declared on its
title.

A flavour can be **hidden from the catalogs**. This is useful during flavour
transitions, for example when a recipe stops producing `mini` and `maxi` flavours in
favour of `full`. Hiding a flavour removes its books from the collection catalogs
without deleting anything: the ZIM files stay on the filesystem so ongoing downloads
keep working, and the flavour can be shown again at any time. Once new books cover the
expected flavours, the old flavour can still be deleted if desired.

A flavour can also be put under **temporary manual review**. This overrides the
manual review setting of its title for that flavour only, until the next book of the
flavour is moved to production. When that book is promoted, the CMS proposes to remove
the temporary manual review; the editor may keep it if they prefer.

### Collections

A **collection** is a curated catalog of titles exposed to Kiwix readers through a
`catalog.xml` file (and an equivalent `opds.xml` feed).

Each collection:

- is associated with a single **warehouse** (the storage where its ZIM files live)
- defines the base URLs used to build the download and view links for its books
- can be **private** (restricted to editors who have been granted access) or public
- can define per-collection **thresholds** for detecting suspicious changes in article
  and media counts

A title is attached to a collection through a `path`, which determines the folder
(relative to the collection's warehouse) where its books are stored.

### Warehouses

A **warehouse** is a storage location where ZIM files physically live. Warehouses are
used to separate concerns such as the quarantine area, the staging area, production
collections and backups. Each book is associated with one or more **locations**, each
pointing to a warehouse, a path and a filename.

### Applications

An **application** is the configuration used to build and publish a branded app for
one flavour of a title to a store. Each application has:

- a **title** and a **flavour**
- a **store**, either `android` or `apple`
- an **application name**, which identifies the branded app (lowercase letters, digits,
  hyphens and underscores only)
- an **enabled** flag

A given title flavour can have at most one application per store, and an application
name must be unique within a store. Applications are listed in the **Apps** screen.

### App Builds

An **app build** is a request to package the latest production book of a title flavour
into a branded application and publish it to a store.

When a build is requested, the CMS:

1. checks that the application is enabled and that no other build for the same
   application is already in progress,
2. derives the content version from the latest `prod` book of the flavour,
3. opens a pull request against the branded app repository,
4. waits for the pull request checks, merges it, and creates a release/tag,
5. triggers the CD workflow which builds and uploads the app,
6. marks the build as uploaded once the CD workflow succeeds.


### Download Statistics

The CMS periodically fetches the daily number of downloads of every title flavour from
the Kiwix download load balancer (through Matomo). These statistics power two things:

- the **Stats** tab of a title, which shows monthly downloads per flavour for the
  current and previous calendar year,
- the **popularity** score of titles, which is periodically recomputed from the most
  recent days of downloads and shown in the titles list and title details.

### Zimfarm Notifications

A **Zimfarm notification** is the message sent by the zimfarm backend to the CMS when a
ZIM file has been produced and verified. The CMS stores each notification, then the
[mill](INTEGRATORS_GUIDE.md#mill) processes it into a **book**. Notifications can be inspected in the
_Zimfarm Notifications_ tab of the _Inbox_, which is useful to understand why a book was
(or was not) created.

### Events

An **event** is an internal message recorded by the CMS to trigger background work. For
example, editing a title records a `title_modified` event that the [mill](INTEGRATORS_GUIDE.md#mill)
consumes to propagate the changes. Events are listed in the _Events_ tab of the _Inbox_; they are
mostly useful for diagnosing why a change has not been processed yet.

### Title Uploads

A **title upload** is a ZIM file uploaded manually through the CMS (rather than one
produced by a regular Zimfarm recipe). When you upload a ZIM this way, the CMS creates
(or reuses) a dedicated `zimwright` recipe on zimfarm and requests a task to process the
file. You can follow the progress of these uploads in the _Upload_ tab of a title.

Uploads can be performed by editors, or by accounts with the `title-uploader` role that
have been granted access to the title. See [Roles & Permissions](#roles--permissions).

## The Lifecycle of a Book

1. Zimfarm notifies the CMS that a new ZIM is available.
2. The [mill](INTEGRATORS_GUIDE.md#mill) turns the notification into a book in **quarantine**.
3. The CMS checks the book against the ZIM specification (mandatory metadata, article
   count, …) and tries to match it to an existing title by name.
4. If the book matches a title, it is attached to it and either:
   - moved to **staging** if manual review is enabled for the title or its flavour, or
     the book has issues, or
   - moved to **prod** if manual review is disabled and the book has no issues.
5. The book enters a **transition**: the `shuttle` physically moves the ZIM file to its
   target warehouse location(s), then the [mill](INTEGRATORS_GUIDE.md#mill) checks that the book is available on
   enough mirrors and live in the library. Download and view links become available
   at the end of this transition.
6. Retention rules are applied to `prod` books, and books that are no longer needed are
   scheduled for deletion.

Books that fail validation or do not match any title remain in quarantine and appear in
the **Inbox** for an editor to review.

## Roles & Permissions

The CMS uses a role-based access control system. Each account has a single role that
determines what it can do. Collection-scoped roles are further restricted to the
collections explicitly granted to the account, and the `title-uploader` role is
restricted to the titles explicitly granted to it.

| Role                  | Scope                          | Description                                                                                                                                                                                                                                                                          |
| --------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **admin**             | Everything                     | Full access to everything. Only role that can create and delete collections, delete applications, and create/update/delete accounts.                                                                                                                                                 |
| **global-editor**     | All collections and titles     | Full access to all books and titles (including archiving), can read accounts, and read/update all collections. Can create/update applications and trigger builds on any title.                                                                                                       |
| **collection-editor** | Granted collections and titles | Can manage books, and read/update titles (but not archive them) and collections, within the collections they are granted access to. Can create/update applications for these titles, but can only trigger a build after being granted build access to the title. Cannot manage accounts. |
| **collection-viewer** | Granted collections and titles | Read-only access to books, titles and collections within the collections they are granted access to.                                                                                                                                                                                 |
| **global-viewer**     | All collections and titles     | Read-only access to all books, titles and collections. Can also read accounts.                                                                                                                                                                                                       |
| **title-uploader**    | Granted titles                 | Can view the titles it has been granted access to and upload ZIM files to them. Cannot access the Collections, Apps or Users screens.                                                                                                                                                |
| **public-viewer**     | Public content                 | Lowest-privilege authenticated role. It grants no CMS permission beyond what an unauthenticated visitor can access (public catalogs). This is the role given to accounts automatically created on first OAuth login.                                                              |
| **zimfarm**           | Machine account                | Can read and create Zimfarm notifications. Reserved for the Zimfarm backend machine account and cannot be created through the UI.                                                                                                                                                    |

Additional role-level rules:

- **Granting upload access**: accounts with `title:update` permission on a title (admins,
  global editors, and collection editors for titles in their collections) can grant a
  `title-uploader` account access to that title from the title's _Upload_ tab.
- **Granting build access**: collection editors can only trigger app builds for titles
  they have been explicitly granted build access to. Admins and global editors in addition to
  triggering any application builds can grant build access to collection editors.
  Build access is granted from the _Apps_ screen (see [Apps](#apps)).
- **Visibility**: users only see the titles, books, collections and applications they
  have access to.

## Using the UI

### Inbox

The **Inbox** has three tabs:

- **Books**: the list of books that need attention — books with errors,
    books that could not be matched to a title, and books awaiting a decision.
- **Zimfarm Notifications**: the notifications received from zimfarm which have not been
    processed or resulted in the creation of a book. Opening one shows its content and events,
    which is helpful for diagnosing why it is still pending or why book creation was rejected.
- **Events**: the internal events recorded by the CMS. These events are processed by a
    background task in the [mill](INTEGRATORS_GUIDE.md#mill)

From a book you can inspect its metadata and issues, attach it to a title, delete it, or
promote it once its issues are resolved.

### Titles

The **Titles** screen lists all non-archived titles, sorted by popularity or by name.
From here you can create titles, and archive or merge several titles at once. Archived
titles are available through the _Archived Titles_ screen.

A title detail page is organized into tabs:

- **Info**: the title's metadata, popularity, collections, events, and associated
  books.
- **Books**: the books attached to the title, grouped by flavour, with a status filter.
- **Stats**: monthly download statistics per flavour for the current and previous
  calendar year.
- **History**: the change history of the title. Useful to see who made changes to a
  title and why, and to revert a change.
- **Edit**: edit the title's metadata, associated collections, and flavours. Removing a
  flavour has the implication that its books are marked for deletion.
- **Upload**: upload a ZIM file manually and follow the processing status of the
  title's uploads. Editors can also use _Manage Upload Access_ to grant
  `title-uploader` accounts access to this title.
- **Archive**: archive or restore the title.

When you edit a title's metadata, the CMS can offer to propagate the change to the
underlying zimfarm recipe (this requires your own Zimfarm credentials — see the
[Integrators Guide](INTEGRATORS_GUIDE.md)).

### Books

The **Books** screen lists books across all location kinds and lets you filter by
status, flavour, issue, and more. Opening a book shows its metadata, issues, locations,
and history. Depending on your permissions, you can:

- update a book's flavour
- **promote** a book to `prod` (after resolving issues). The API will provide a list of
  mandatory and optional actions you should apply to fix the book issues and move book
  to `prod`.
- **unpromote** a book back to `staging`
- **back up** a book (and remove a backup)
- **delete** a book (immediately or after a delay)
- **recover** a deleted book from its backup
- attach a book to a title

### Collections

The **Collections** screen lists collections and lets you filter by name and visibility
(public/private). Admins can create collections; global editors and collection editors
can edit the collections they have access to.

On a collection detail page you can view its info (warehouse, base URLs, privacy,
thresholds), browse its history, and edit its settings. Each collection exposes:

- a `catalog.xml` file at `/collections/{id_or_name}/catalog.xml`, consumed by Kiwix
  readers,
- an `opds.xml` feed at `/collections/{id_or_name}/opds.xml`.

**NOTE**: `catalog.xml` format is maintained for legacy purposes and will be phased out in favour
of the `opds.xml` format once [kiwix-serve](https://wiki.kiwix.org/wiki/Kiwix-serve) is updated.

### Apps

The **Apps** screen lists the applications configured for Android and Apple. You can
filter them by name and store, and open an application to:

- view its title, flavour, latest production book, and build history,
- **build** the application for its store,
- **manage build access**, i.e. grant or revoke the collection editors allowed to build
  applications,
- edit the application name and enabled flag,
- view and revert its history,
- delete it (admins only).

When a build is requested, the CMS first checks whether the current content version was
already built successfully and, if so, asks whether you want to build it again. Only one
build per application can be in progress at a time. The build list shows the status,
phase, content version, pull request, release and workflow links, and the build events.


### Users

The **Users** screen lists accounts. Admins can create accounts, change roles, grant
`collection-editor` and `collection-viewer` accounts access to specific collections,
reset passwords, and delete accounts. The role selector includes all the roles described
in [Roles & Permissions](#roles--permissions).

Public viewers are hidden by default; use _Show Viewers_ to display them. The Zimfarm
machine account is not shown in the UI. Creating a collection-scoped account requires
selecting at least one collection.
