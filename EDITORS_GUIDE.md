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
  - [Zimfarm Notifications](#zimfarm-notifications)
  - [Title Uploads](#title-uploads)
- [The Lifecycle of a Book](#the-lifecycle-of-a-book)
- [Roles & Permissions](#roles--permissions)
- [Using the UI](#using-the-ui)
  - [Inbox](#inbox)
  - [Titles](#titles)
  - [Books](#books)
  - [Collections](#collections)
  - [Users](#users)
  - [Zimfarm Notifications](#zimfarm-notifications-1)

## What is the CMS?

The CMS is the component of the Kiwix stack that catalogs the ZIM files produced by the
[zimfarm](https://github.com/openzim/zimfarm). It receives a notification every time a
new ZIM is produced, checks that the ZIM meets openZIM's requirements, and
associates it with a **title** (a series of related ZIM files) placed in one or more
**collections** (the catalogs exposed to Kiwix readers).

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
  (e.g. the title is still marked `unstable`, or the book has issues).
- **`prod`**: the book is published. A book is published automatically if it's
  associated title is marked `stable` and it has no issues. In the failure of
  automatic movement to `prod` due to book issues, editor has to manually move book
  and resolve any fixable issues along the way.
- **`to_delete`**: the book has been scheduled for deletion.
- **`deleted`**: the book's files have been removed.

Books can also carry **issues**, which describe problems that prevent a book from being
promoted to `prod`. Common issues include missing mandatory metadata, unsupported
languages, unexpected article/media count changes, recipe mismatches, or zimcheck
errors.

### Titles

A **title** is the logical grouping of all the books that represent the same content
across flavours and across time. For example, the `wikipedia_en_all` title groups every
English Wikipedia ZIM, whatever its flavour or version.

A title has:

- a unique **name** (e.g. `wikipedia_en_all`, `gutenberg_fr_all`)
- the ZIM metadata used to describe the content: `title`, `creator`, `publisher`,
  `description`, `language`, `illustration`, `long_description`, `license`,
  `relation`, `source`
- a **maturity**, either `unstable` or `stable`. Books belonging to titles with maturiy of `stable` will be automatically moved to `staging` if they have no issues while those marked as `unstable` will unconditionally be moved to `staging`.
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

### Collections

A **collection** is a curated catalog of titles exposed to Kiwix readers through a
`catalog.xml` file.

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

### Zimfarm Notifications

A **Zimfarm notification** is the message sent by the zimfarm backend to the CMS when a
ZIM file has been produced and verified. The CMS stores each notification, then the
`mill` processes it into a **book**. Notifications can be inspected in the UI, which is
useful to understand why a book was (or was not) created.

### Title Uploads

A **title upload** is a ZIM file uploaded manually through the CMS (rather than one
produced by a regular Zimfarm recipe). When you upload a ZIM this way, the CMS creates
(or reuses) a dedicated `zimwright` recipe on zimfarm and requests a task to process the
file. You can follow the progress of these uploads in the _Upload_ tab of a title.

## The Lifecycle of a Book

1. Zimfarm notifies the CMS that a new ZIM is available.
2. The `mill` turns the notification into a book in **quarantine**.
3. The CMS checks the book against the ZIM specification (mandatory metadata, article
   count, …) and tries to match it to an existing title by name.
4. If the book matches a title, it is attached to it and either:
   - moved to **staging** if the title is still `unstable` or the book has issues, or
   - moved to **prod** if the title is `stable` and the book has no issues.
5. The `shuttle` physically moves the ZIM file to its target warehouse location(s).
6. Retention rules are applied to `prod` books, and books that are no longer needed are
   scheduled for deletion.

Books that fail validation or do not match any title remain in quarantine and appear in
the **Inbox** for an editor to review.

## Roles & Permissions

The CMS uses a role-based access control system. Each account has a single role that
determines what it can do:

| Role                  | Description                                                                                                                                                 |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **admin**             | Full access to everything, including user management and all CRUD operations on titles, books and collections.                                              |
| **global-editor**     | Full access to all books and titles (including archiving), can read accounts, and read/update all collections.                                              |
| **collection-editor** | Can manage books and read/update titles and collections, but only for the collections they are granted access to. Cannot archive titles or manage accounts. |
| **viewer**            | Read-only. Can authenticate but cannot modify anything.                                                                                                     |

> **Note:** the `zimfarm` role also exists but is reserved for the machine account used
> by the Zimfarm backend to push notifications. It cannot be created through the UI.

## Using the UI

### Inbox

The **Inbox** lists books in **quarantine** that need attention — books with errors,
books that could not be matched to a title, and books awaiting a decision. From the
inbox you can:

- open a book to inspect its metadata and issues
- attach a book to a title
- delete a book
- promote a book to `prod` once its issues are resolved

### Titles

The **Titles** screen lists all non-archived titles. From here you can create, edit,
archive and merge titles, and open a title to manage its details.

A title detail page is organized into tabs:

- **Details**: the title's metadata, its collections, its events, and the books
  attached to it.
- **Flavours**: the flavours of the title and their linked zimfarm recipe. You can
  remove a flavour from here. Deleting a flavour has the implication that books are
  marked for deletion.
- **History**: the change history of the title. Useful to see who made changes to a
  title and the reason why they made a change.
- **Edit**: edit the title's metadata and associated collections.
- **Upload**: upload a ZIM file manually and follow the processing status of the
  title's uploads.
- **Archive**: archive the title.

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

The **Collections** screen lists collections. You can create a collection, edit its
name, download/view base URLs, privacy, and thresholds, and browse the titles it
contains. Each collection exposes a `catalog.xml` file (at
`/collections/{id_or_name}/catalog.xml`) that Kiwix readers consume.

### Users

The **Users** screen lists accounts. Admins can create accounts, change roles, grant
`collection-editor` accounts access to specific collections, reset passwords, and
delete accounts.

### Zimfarm Notifications

The **Zimfarm Notifications** screen lists the notifications received from zimfarm.
Opening a notification shows its content and events, which is helpful for diagnosing
why a book was created, rejected, or is still pending.
