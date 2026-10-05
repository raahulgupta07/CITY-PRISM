# Go live and support (Phase 6, 29 to 30 Oct 2026)

This is the runbook for putting City Prism live in the City AI estate, helping
owners fill in their assessments, and preparing the steering committee pack.

## 1. Where it runs

City Prism is one container with SQLite, so it runs on **one server with its
own disk**:

| Part         | Choice                                                                                                                                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Server       | One EC2 instance in ap-southeast-1, in the CityGPT VPC, private subnet. `t3.small` is enough for 200 projects. Amazon Linux 2023 with Docker and the Compose plugin.                               |
| Disk         | The root EBS volume (gp3, 20 GB, encrypted) holds the Docker volume `prism-data`.                                                                                                                 |
| HTTPS        | An Application Load Balancer with an ACM certificate (the CityGPT one, with a host rule, if the network team allows it). Listener HTTPS 443 → target group HTTP 8080. Redirect HTTP 80 to HTTPS. |
| Health check | Target group: `GET /api/health`, success code 200.                                                                                                                                               |
| Firewall     | The server's security group lets in port 8080 from the load balancer only. No public IP.                                                                                                          |
| Outbound     | HTTPS to `openrouter.ai` (the AI) and to the identity provider (Entra ID: `login.microsoftonline.com`). Same egress rules as CityGPT.                                                             |
| Image        | Amazon ECR repository `city-prism`.                                                                                                                                                               |

Do not use ECS Fargate with EFS, or run more than one copy: SQLite needs one
writer on a local disk. If more is ever needed, switch to PostgreSQL (README).

## 2. First deploy (29 Oct)

1. **Build and push the image** (from a machine with Docker and AWS access):

   ```sh
   TAG=$(date +%F)
   REPO=<account>.dkr.ecr.ap-southeast-1.amazonaws.com/city-prism
   aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin ${REPO%/*}
   docker build --platform linux/amd64 -t $REPO:$TAG .
   docker push $REPO:$TAG
   ```

2. **Register the app with Entra ID** (README → Company sign-in). Redirect URI:
   `https://<address>/api/auth/sso/callback`.

3. **On the server**, put `docker-compose.prod.yml` and a `.env` in `/opt/city-prism`:

   ```sh
   ENV=prod
   SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
   PUBLIC_URL=https://<address>
   OIDC_ISSUER=https://login.microsoftonline.com/<tenant id>/v2.0
   OIDC_CLIENT_ID=<client id>
   OIDC_CLIENT_SECRET=<client secret>
   OIDC_ALLOWED_DOMAINS=cityholdings.com.mm
   OPENROUTER_API_KEY=<key>
   LLM_MODEL_FAST=<model id from the CityGPT routing>
   LLM_MODEL_DEFAULT=<model id from the CityGPT routing>
   ```

   Then `chmod 600 .env`. Keep `SECRET_KEY` the same across restarts, or
   everyone is signed out.

4. **Start it:**

   ```sh
   cd /opt/city-prism
   export PRISM_IMAGE=<REPO>:<TAG>
   docker compose -f docker-compose.prod.yml up -d
   docker compose -f docker-compose.prod.yml logs -f      # wait for "Uvicorn running"
   ```

   On first start the app creates the database and loads the 40 questions, the
   admin (rahulgupta@cityholdings.com.mm) and the 12 projects.

5. **Backups** (see section 4) before anyone enters data.

6. Run the go-live checks (section 3).

## 3. Go-live checks

- [ ] `https://<address>/api/health` returns `{"status":"ok"}`. HTTP redirects to HTTPS.
- [ ] Sign in with a company account works. A non-company account is refused.
- [ ] The admin signs in and sees Admin. In Admin → Users and roles, set the approvers and other admins.
- [ ] The portfolio shows 12 projects with the expected verdicts.
- [ ] On one test project: answer a question by hand, run one Interview turn, read one piece of evidence, write a brief. Then archive the test project.
- [ ] Signed in as admin, `https://<address>/api/admin/ai-calls` lists those calls, with model, tokens and cost.
- [ ] Export → Excel and CSV download.
- [ ] Open it on a phone.
- [ ] A backup runs (`docker exec city-prism python -m app.backup`) and an EBS snapshot exists.
- [ ] Restore was tried once on a copy (section 4).
- [ ] One pass with a screen reader (VoiceOver or NVDA) on sign in, Assess and the brief.

## 4. Backups

Two layers:

1. **Nightly copy** of the database while the app runs. On the server,
   `crontab -e`:

   ```
   15 1 * * * docker exec city-prism python -m app.backup --keep 14 >> /var/log/prism-backup.log 2>&1
   ```

2. **Daily EBS snapshot** of the server's volume with Amazon Data Lifecycle
   Manager (keep 14). This also covers losing the server.

**Restore** (test this once before go-live):

```sh
docker compose -f docker-compose.prod.yml stop
docker run --rm -v prism-data:/data alpine sh -c \
  'cp /data/backups/<file>.db /data/prism.db && rm -f /data/prism.db-wal /data/prism.db-shm'
docker compose -f docker-compose.prod.yml start
```

## 5. Updates and rollback

To ship a fix:

1. Run the checks in the README. Build and push a new tag.
2. On the server: back up, then switch the image.

   ```sh
   docker exec city-prism python -m app.backup
   export PRISM_IMAGE=<REPO>:<new tag>
   docker compose -f docker-compose.prod.yml up -d
   ```

   Migrations run on start. People may need to reload the page.

**Rollback:** set `PRISM_IMAGE` back to the old tag and `up -d`. If the new
version changed the database (a new migration), also restore the backup taken
just before the update. Answers saved after that backup are lost, so check
the answer history first.

## 6. Support while owners fill in (29 to 30 Oct)

**Send owners this note** (edit the address and dates):

> City Prism is live at https://<address>. Sign in with your City Holdings account.
> Open your project and answer the 40 questions. You can answer by hand, chat
> with the agent (Interview), or paste a project document (Read evidence).
> Answers from the AI are marked until you confirm them. Please finish by
> 30 Oct. Problems or questions: <contact>.

**When someone reports a problem**, find out the project, the screen and the time, then:

| Problem                                      | Where to look                                                                                                                                                                                                                                                           |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cannot sign in                               | `docker logs city-prism \| grep prism.auth` gives the reason. `not_allowed`: wrong email domain. `token` or `provider`: check `OIDC_*` settings and the app registration. `expired`: try again in one tab.                                                         |
| Cannot see or edit a project | Admin → Users and roles: owners edit only the projects they own; reviewers and admins edit all. Archived projects cannot be edited. |
| The agent fails or is slow | Signed in as admin, open `https://<address>/api/admin/ai-calls`: each call has `ok` and `error`. `timeout`: raise `LLM_TIMEOUT_SECONDS`. If the agent says "The AI is not set up yet", the key or a model ID is missing in `.env`. |
| "An answer changed and I did not change it" | The project's Changes tab shows who changed what, and when. Answers from the AI stay marked until confirmed.                                                                                                                                                           |
| The verdict looks wrong | The verdict comes from fixed rules (SPEC 3.3): the lowest dimension score decides, and any "No" caps its dimension at 3.0. Check the answers in the weakest dimension. It is a bug only if the rules give a different result. |
| Wording of a question | Admin → Question set. Dimensions 1 and 2 are draft wording. Changes apply to everyone at once and do not change saved answers. |

Fix bugs with the update steps in section 5. Note each fix and keep features
outside the spec for later (SPEC 11).

## 7. Steering committee pack (30 Oct)

The pack is made from the portfolio and the decision briefs:

1. **Portfolio summary:** on the Portfolio, select **AI portfolio summary**.
   Copy the text into the cover note. Check it against the table; the
   verdicts in the table come from the rules and are the ones that count.
2. **Portfolio table:** Export → Excel. The "Portfolio" sheet has one row per
   project (verdict, weakest dimension, scores); the "Answers" sheet has all
   answers with evidence.
3. **One brief per project that needs a decision:** open the project →
   Decision brief → Write brief with AI (or Rewrite brief if answers changed).
   The approver reads it and selects Approve decision.
4. **Save each brief as PDF:** on the brief, press Ctrl+P (Cmd+P on a Mac)
   and choose Save as PDF. The printout is always light, keeps the verdict
   band, and leaves out the menu and buttons.
5. Put the cover note, the Excel file and the brief PDFs together. Briefs with
   open questions say so; the verdict can change as owners answer more.

A brief in the official City Holdings template, and sending it from the app,
are planned for later (SPEC 11).
