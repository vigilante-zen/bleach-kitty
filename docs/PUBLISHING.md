# Put this package on GitHub

Create an empty GitHub repository in your account, without adding a README or license remotely. Then run these commands from this package directory (replace the remote URL with your repository's URL):

```sh
git add .
git commit -m "Package Bleach Kitty terminal theme"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/bleach-kitty.git
git push -u origin main
```

If you downloaded the archive rather than using the prepared local Git directory, run `git init -b main` first. Git may require you to configure your name and email before the first commit. No account information or remote URL has been added to this package.

For an existing GitHub repository, copy this directory's contents into the desired subdirectory, omitting its `.git` directory. Commit from your existing repository root. The included CI workflow belongs at that repository's `.github/workflows/` root; if you place the theme in a subdirectory, adjust its command paths before enabling CI.

The release archive belongs in GitHub Releases, not inside the Git repository; `.gitignore` excludes archives. Commit the PNG artwork directly or establish your own Git LFS workflow before the initial commit. Current PNGs are below 100 MiB each. Review `docs/ARTWORK.md` before publishing.
