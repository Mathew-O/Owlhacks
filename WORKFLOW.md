# How we work on this repo

More than one person is pushing. Follow this or you will clobber someone.

## Every single time you sit down

```
git pull --rebase
```

Do this BEFORE you edit anything. Not after.

## Every time you finish a chunk

```
git add -A
git commit -m "short: what changed"
git pull --rebase
git push
```

The pull before push is not optional. It is what stops the rejection.

## If push gets rejected

Someone pushed while you were working.

```
git pull --rebase
```

If it stops on a conflict: open the file, pick the right lines, delete the `<<<<<<<` `=======` `>>>>>>>` markers, then

```
git add <file>
git rebase --continue
git push
```

## Notes between pushes

Add one line to CHANGELOG.md with every push. Newest on top. Name, what you changed, anything the next person has to know.

## Rules

- Never commit .env. It has keys. .gitignore already blocks it.
- Never commit .venv, __pycache__, *.db. Already blocked.
- Claim a file in the group chat before you edit it. Two people in models.py at once is a bad time.
- Commit messages say what changed, not "update" or "fix".
- Run `python -m tests.smoke` before you push. If it fails, do not push.

## First time setup

```
git clone https://github.com/Mathew-O/Owlhacks.git
cd Owlhacks\ticketdesk
copy .env.example .env
setup.bat
run_ui.bat
```
