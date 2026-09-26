# NEA Toolbox - Future Development & Systems Integration Technical Roadmap

**Audience:** Network Manager / Microsoft 365 Administrator / MIS support  
**Current production branch:** `production-local-workflow`  
**Status:** Technical planning document; no live tenant or pupil-data changes are made by this document.

## Purpose

This document records the proposed next stages for NEA Toolbox after the local production workflow. The next stages depend primarily on school infrastructure, identity, MIS integration, Microsoft 365 configuration, permissions and information-governance decisions.

The target is to remove repeated manual handling while preserving a safe local fallback: class lists should ideally come from an authoritative school source, and successfully identified photographs should be transferable into managed Microsoft 365 storage without putting real pupil data in GitHub.

## Recommended direction

1. Keep Excel/CSV roster import and local output permanently as a fallback.
2. Investigate **Microsoft 365 Education / Microsoft Graph first**, because it may provide teacher classes, class membership and managed storage through the school's existing identity platform.
3. Treat **direct SIMS integration as a later option** unless Microsoft 365 lacks the identifiers needed to map pupils reliably.
4. Do not use Class Charts as the primary API source unless Tes/Class Charts provides a supported API or the school's existing Wonde/Xporter arrangement can expose an authorised feed.
5. Prefer a **school-controlled SharePoint/Teams evidence location** over broad application access to every pupil OneDrive unless school policy specifically requires personal OneDrive storage.

## 1. Current application state

The production-local-workflow version already separates the workflow into reusable stages:

1. Load Excel/CSV roster locally.
2. Generate candidate QR cards.
3. Read photographs from camera/SD-card/local folders.
4. Match QR payload to candidate.
5. Copy images into `Group / Student - Candidate` folders.
6. Place unreadable/ambiguous images into `Manual_Check_Required`.
7. Record CSV audit reports and support manual assignment.

The future design should preserve the photo-recognition/safety logic and add interchangeable roster providers and storage destinations.

## 2. Proposed architecture

| Layer | Current | Future | Reason |
|---|---|---|---|
| Roster provider | Excel | Microsoft Graph; optional SIMS/Wonde/Xporter | Swap data sources without changing sorting logic |
| Identity mapper | Candidate number | Candidate ↔ MIS ID ↔ Entra ID/UPN | Separate exam identity from cloud identity |
| Photo matcher | QR candidate number | Unchanged | Avoid names/emails in QR payload |
| Storage destination | Local | SharePoint/Teams / optional OneDrive | Local-first plus managed upload |
| Authentication | None | Entra ID/MSAL; vendor auth if needed | Controlled access/token handling |
| Audit | Local CSV | Local audit + Microsoft object IDs/upload status | Traceability and safe retries |

**Target flow:** sign in → choose class → resolve candidate identities → sort locally → upload verified matches → retry failed uploads → review exceptions.

## 3. Class-list integration

### 3.1 Microsoft Graph Education

Microsoft Graph Education exposes schools, classes, teachers, students and memberships. A teacher can query their own classes using endpoints such as:

```
GET https://graph.microsoft.com/v1.0/education/me/classes
GET https://graph.microsoft.com/v1.0/education/classes/{class-id}/members
GET https://graph.microsoft.com/v1.0/education/users/{student-id}
```

For a signed-in work/school user, Microsoft documents delegated `EduRoster.ReadBasic` as the least-privileged scope for class/roster basics. Broader application access uses permissions such as `EduRoster.Read.All` and requires administrator consent.

**Critical dependency:** the tenant must contain usable education roster objects. The Network Manager must confirm how DHFS provisions Teams/classes (e.g. School Data Sync or another MIS connector) and whether `educationClass` / `educationUser` data is populated.

Microsoft's `educationStudent` object can contain `externalId` and `studentNumber`, but these are populated by the source system and must not be assumed to equal the examination candidate number.

### 3.2 SIMS

SIMS supports third-party integration routes with controlled data access. The exact method depends on the school's SIMS product/version/deployment and licensing/partner arrangements. SIMS documentation describes application registration where requested data fields/securables are declared and reviewed.

Potential routes:
- supported direct SIMS API/OData;
- an existing school integration broker;
- Wonde;
- Xporter;
- a scheduled, school-generated export.

Do not screen-scrape SIMS and do not embed personal SIMS credentials in the application.

### 3.3 Class Charts

Class Charts already imports MIS classes and its support material references Wonde/Xporter for SIMS integrations. This may identify an existing approved data route, but it does not prove a supported API is available for NEA Toolbox.

Ask whether DHFS Class Charts uses Wonde or Xporter and whether the school contract permits an internal app to consume roster data via that provider. Avoid unofficial/reverse-engineered Class Charts endpoints for production pupil data.

### 3.4 Roster-source decision

| Option | Effort | Governance | Candidate mapping | Suggested role |
|---|---|---|---|---|
| Microsoft Graph Education | Medium | Entra app + admin consent | Verify | First POC |
| Direct SIMS | Medium-high/vendor-dependent | SIMS support/approval | Likely strongest | Use if Graph lacks identifiers |
| Wonde/Xporter | Medium/contract-dependent | Existing school/vendor approval | Verify | Strong alternative |
| Class Charts direct | Unknown | Vendor support required | Unknown | Only if officially supported |
| Excel/CSV | Complete | Local handling | Known working | Permanent fallback |

## 4. Microsoft authentication / Entra registration

NEA Toolbox is a desktop application. Recommended design:

- single-tenant Microsoft Entra app registration;
- public-client desktop authentication using MSAL;
- interactive system-browser sign-in with modern OAuth/OIDC/PKCE;
- **no client secret embedded in the EXE or repository**;
- secure MSAL token caching;
- signed-in teacher identity used to restrict visible classes where possible.

Suggested roster-only POC permissions:
- `openid`, `profile`, `offline_access` as required by the authentication flow;
- `EduRoster.ReadBasic`;
- `User.Read` if required for standard user profile/sign-in.

Do not request broad file-write permissions during the roster POC.

## 5. Microsoft 365 destination options

### 5.1 Preferred: SharePoint / Teams class or department storage

Teams class files are backed by SharePoint/Microsoft 365 Group storage. A controlled class/department evidence library generally offers stronger teacher ownership, retention and handover than pupil-owned OneDrive.

Possible operations:

```
GET /groups/{class-group-id}/drive
POST /drives/{drive-id}/items/{parent-id}/children
PUT /drives/{drive-id}/items/{parent-id}:/{filename}:/content
POST /drives/{drive-id}/items/{parent-id}:/{filename}:/createUploadSession
```

Recommended implementation:
- predictable evidence root, e.g. `/NEA Evidence/2026-27/11A-Food/`;
- stable per-pupil internal identifier for folder association;
- save drive/site/item IDs rather than repeatedly searching by names;
- idempotent uploads using hash/object-ID tracking;
- never silently overwrite a different photograph;
- local copy remains intact until upload is verified.

Microsoft Graph supports **Selected** permission models for SharePoint/OneDrive resources, allowing access to be granted to specific sites/lists/items/files instead of granting automatic tenant-wide access.

### 5.2 Direct pupil OneDrive

Directly writing into other users' OneDrives is a higher-risk design. A teacher's delegated `Files.ReadWrite` does not automatically grant access to every pupil's personal drive. Application permissions such as `Files.ReadWrite.All` can be very broad and require explicit admin/security review.

If personal OneDrive is mandatory, investigate in this order:

1. **App folder** using `Files.ReadWrite.AppFolder`, if the per-user provisioning and teacher-access model works for the tenant.
2. **Selected-resource permissions** where practical.
3. Broad application permission only as a last resort.

Also consider that pupils can delete content from their own OneDrive. If photographs are intended to be controlled NEA evidence, a teacher/department-owned location is normally more robust.

## 6. Required identity mapping

Names are not safe primary keys. The runtime mapping should ideally include:

- exam candidate number;
- MIS pupil ID;
- Entra object ID;
- UPN/email;
- class ID;
- destination drive/item IDs.

Matching hierarchy:

1. Candidate number directly available from authoritative roster/MIS data.
2. Stable MIS ID available in both the exam data and Microsoft/SIMS data.
3. Controlled local mapping held on school storage (never GitHub).
4. Never auto-match solely by display name when ambiguous.

## 7. Data protection and operational controls

- Apply least privilege; separate roster-read and file-write capabilities.
- Never store secrets, tokens, real rosters, real photos or real mappings in GitHub.
- Decode/sort locally first; upload a verified copy afterwards.
- Do not log tokens. Minimise names in diagnostic logs.
- Record upload source hash, target object ID, status, timestamp and error code.
- Make retries idempotent.
- Keep ambiguous photos local until explicitly assigned.
- Use HTTPS/TLS only and support school proxy/firewall/SSL inspection requirements.
- Define retention, access, deletion and leaver handling with IT/DPO.
- Consider code signing and central Windows deployment once IT supports the tool.

## 8. Information required from the Network Manager

1. How are classes and pupils currently provisioned into Microsoft 365/Teams: SDS, SIMS connector, Wonde, Xporter, another sync or manual Teams?
2. Do Microsoft Graph Education endpoints return the teacher's real classes and class members?
3. For a pupil, what values appear in `student.externalId` and `studentNumber`?
4. Which SIMS product/version/deployment is in use and which supported integration route is available?
5. Is Class Charts fed by Wonde or Xporter, and can that approved connector support an internal roster feed?
6. Does IT prefer interactive delegated authentication or an application/service model?
7. Where should NEA evidence live: department SharePoint, class Team, assessment site or pupil OneDrive?
8. What Graph permissions would IT approve? Can Selected permissions be used?
9. Are all relevant pupil OneDrives provisioned, and is application writing to them acceptable?
10. What proxy/firewall/SSL-inspection constraints apply?
11. What retention/backup/access requirements apply to NEA photographic evidence?
12. How should the Windows app be deployed: Intune, software centre, network share, managed installer, etc.?

## 9. Proposed POC sequence

### Phase 0 - Infrastructure discovery
No production changes. Verify provisioning, Graph visibility, pupil identifiers and storage policy.

### Phase 1 - Read-only Microsoft roster
Register Entra app, add MSAL sign-in, retrieve only the signed-in teacher's classes and selected class membership. No file uploads.

### Phase 2 - Identity resolution
Prove deterministic candidate-number mapping. If Graph is insufficient, test SIMS/Wonde/Xporter or controlled local mapping.

### Phase 3 - SharePoint/Teams upload sandbox
Use a test Team/site and fictional accounts/files. Implement destination abstraction, folder creation, safe conflict handling, retry and audit.

### Phase 4 - Limited real pilot
One teacher, one class, small controlled sample. Local copy remains primary. Manually verify every identity and destination.

### Phase 5 - Production hardening
Code signing/deployment, permission review, logs, support documentation, retention process, recovery procedure and update process.

### Phase 6 - Optional pupil OneDrive
Only if still required after governance review.

## 10. Technical acceptance criteria

- Teacher signs in using the school account; NEA Toolbox never collects the password itself.
- Only authorised classes are shown.
- Every automatically uploaded pupil has a deterministic candidate ↔ Microsoft identity mapping.
- Ambiguous identities cannot auto-upload.
- Successful uploads have a local audit record containing destination identifiers.
- Re-running an import does not create uncontrolled duplicates.
- Network failure leaves local sorted files intact and marks uploads for retry.
- No tokens, secrets, real rosters/photos/mappings enter GitHub.
- IT can revoke access centrally in Entra/Microsoft 365.
- Excel/CSV + local-only mode remains functional if cloud services are unavailable.

## 11. Suggested GitHub epics

- **EPIC-AUTH** - MSAL/Entra authentication, tenant configuration, sign-in/out, secure token cache.
- **EPIC-ROSTER-GRAPH** - Graph class picker, memberships, paging, immutable IDs.
- **EPIC-IDENTITY** - candidate mapping, validation UI, duplicate/unmatched handling.
- **EPIC-STORAGE** - destination abstraction, local + SharePoint/Teams, upload queue, retry/backoff, hash/conflict handling.
- **EPIC-ADMIN** - diagnostics/configuration UI and permission tests.
- **EPIC-PRIVACY** - data minimisation, secure logs, retention/cache controls.
- **EPIC-SIMS** - supported SIMS/Wonde/Xporter provider only if required after discovery.
- **EPIC-ONEDRIVE** - optional personal-OneDrive destination after security approval.

## 12. Recommended first meeting outcome

The first Network Manager meeting only needs to establish four facts:

1. how Teams classes are provisioned today;
2. whether Graph Education exposes those classes and useful pupil identifiers;
3. whether a controlled SharePoint/Teams evidence location is preferable to pupil OneDrive;
4. what authentication/permission model IT will approve for a small test application.

Once these are known, implementation can be specified without guessing about school infrastructure.

## Technical references

- Microsoft Graph Education overview: https://learn.microsoft.com/en-us/graph/api/resources/education-overview?view=graph-rest-1.0
- List classes of an educationUser: https://learn.microsoft.com/en-us/graph/api/educationuser-list-classes?view=graph-rest-1.0
- educationUser / educationStudent: https://learn.microsoft.com/en-us/graph/api/resources/educationuser?view=graph-rest-1.0
- Microsoft Graph permissions: https://learn.microsoft.com/en-us/graph/permissions-reference
- Selected permissions: https://learn.microsoft.com/en-us/graph/permissions-selected-overview
- OneDrive/SharePoint app folder: https://learn.microsoft.com/en-us/graph/onedrive-sharepoint-appfolder
- Create folder: https://learn.microsoft.com/en-us/graph/api/driveitem-post-children?view=graph-rest-1.0
- Upload file: https://learn.microsoft.com/en-us/graph/api/driveitem-put-content?view=graph-rest-1.0
- Upload session: https://learn.microsoft.com/en-us/graph/api/driveitem-createuploadsession?view=graph-rest-1.0
- School Data Sync: https://learn.microsoft.com/en-us/graph/msgraph-onboarding-sds
- SIMS integration/application configuration: https://id.sims.co.uk/support/wiki/128/create-or-edit-an-application
- Class Charts SIMS/Wonde/Xporter guidance: https://class-charts.help.tes.com/support/solutions/articles/75000141751-how-to-add-aspects-from-sims
- Tes Class Charts MIS overview: https://www.tes.com/for-schools/class-charts
