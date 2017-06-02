# What is this?
This is a fork of [acd\_cli](https://github.com/yadayada/acd_cli) that works around Amazon's bullshit by using the OAuth endpoint for the ACD desktop apps.

# Will Amazon ban me if I use this?
Maybe. This fork makes some cursory attempts to appear as though it's the real app, but it's quite possible they can detect that it's not. I take no responsibility if they ban you because you used this. In fact I would recommend your primary use for it be getting your data off ACD and on to a less user-hostile service.

# Will Amazon break this?
Inevitably. I have no intention of perpetuating a game of whac-a-mole. When it breaks, it breaks.

# How do I use this?
You will need access to a Windows machine to obtain the credentials needed to use this fork (Mac should also work, although I haven't tested it).

1. Remove your existing `~/.cache/acd_cli/` folder.
2. Remove your existing acd\_cli installation with `pip uninstall acdcli`.
3. Obtain your refresh token from the <a href="https://www.amazon.com/b?node=16409408011" rel="noreferrer">Drive for Windows app</a>. You can do this in many ways including extracting the credentials from the memory of the app while it's running or sniffing them when they are sent to Amazon. I will describe the memory dump method below.
	1. Make sure you're logged in to Drive.
	2. Right click the drive process in Task Manager and choose "Create dump file".
	3. Open the dump in your favorite hex editor of choice.
	4. Find the string starting "Atnr|". This is your refresh token.
4. Create a file at `~/.cache/acd_cli/oauth.json` with this format:
```json
{
    "access_token": "Put whatever here - it won't be used.",
    "exp_time": 0.0,
    "expires_in": 3600,
    "refresh_token": "Your refresh token here.",
    "token_type": "bearer"
}
```

5. Install this fork with `pip install "git+https://github.com/chrisgavin/cheeky_acd_cli.git"`.
6. Run `acdcli sync` twice (for me it fails the first time due to a missing root node but I think this is an existing bug).
7. Done. acd\_cli should be working again. Praise Bezos.

# Why does this exist?
When I signed up for ACD both acd\_cli and rclone were fully functional. I signed up entirely on the basis of the existance of these apps; I'm a Linux user, even if I wanted to use their official apps I can't and their web interface is absolute shit.

When Amazon banned acd\_cli and rclone they not only made their own service worthless to me, they practially removed my access to data already stored on the service. This is totally unacceptable.

Amazon only need to do one thing to make me happy: allow non-whitelisted apps to access the Drive data for the user that created the security profile. If you don't want other people using using your service in their projects that's fine but I deserve unrestricted access to my own damn data!
