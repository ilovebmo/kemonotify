import os, sys
import requests
import json, pickle
from time import sleep
import logging
import infi.systray, win11toast, webbrowser
import threading


ONE_HOUR: int = 3600
SERVICES: list[str] = [
    "Patreon",
    "Fanbox",
    "Boosty",
    "DLsite",
    "GumRoad",
    "SubscribeStar",
]
BASE: str = "https://kemono.party"
API: str = "https://kemono.party/api/v1"
LOG: str = "logging.log"
ICON: str = "kemono.ico"
IMG: str = "https://img.kemono.su/icons"  # Base link for the image server, but it doesn't work with win11toast


class Log:
    def yellow(msg: str):
        logging.warning(msg)
        print("\x1b[33m" + msg + "\x1b[0m")

    def white(msg: str):
        logging.info(msg)
        print("\x1b[0m" + msg + "\x1b[0m")

    def red(msg: str):
        logging.warning(msg)
        print("\x1b[31m" + msg + "\x1b[0m")
        sys.exit(msg)


class Creator:
    service: str
    name: str
    idn: str

    def __init__(self, service: str, name: str, idn: str):
        self.service = service
        self.name = name
        self.idn = idn

    def latest(self) -> dict:
        return json.loads(
            requests.get(API + f"/{self.service.lower()}/user/{self.idn}").content
        )[0]

    def __repr__(self) -> str:
        return f"{self.name}'s {self.service}"


class Setup:
    time: int
    creators: list[Creator]

    def __init__(self):
        os.system("title Kemonotify")
        os.system("cls")
        Log.white("Starting Kemonotify 🐺")

        try:
            self._creators_list = json.loads(
                requests.get(API + "/creators.txt").content
            )
            Log.white("Got Creators List.")
        except:
            Log.red(f"Couldn't get creators list.")

        self.time = self._get_time()
        Log.white(f"Time set at {self.time} seconds.")

        self.creators = self._get_creators()
        self._hide_console()
        os.system("cls")
        Log.white(
            f"Creators: {', '.join(creator.__repr__() for creator in self.creators)}."
        )

        self._generate_storage()

    def _get_time(self):
        _time = input("Time (default=3600s): ")
        if _time == "":
            return ONE_HOUR

        try:
            return int(_time)
        except ValueError:
            Log.yellow("Invalid Time input!")
            return self._get_time()

    def _get_creators(self) -> list[str]:
        _creators = []
        for service in SERVICES:
            for name in self._parse_creators_by_service(service):
                if name == []:
                    continue
                idn = self._creator_exists(service, name)
                if idn:
                    _creators.append(Creator(service, name, idn))
                else:
                    Log.yellow(f"{name}'s {service} isn't on Kemono.")
        if _creators == []:
            Log.red("No creators listed.")
        return _creators

    def _parse_creators_by_service(self, service: str) -> list:
        names = input(f"{service.capitalize()}: ")
        return (
            self._split_strip(names, ", ") if "," in names else self._split_strip(names)
        )

    def _split_strip(self, string: str, pattern: str = None) -> list[str]:
        return [item.strip() for item in string.split(pattern)]

    def _creator_exists(self, service: str, creator: str) -> bool:
        for existing in self._creators_list:
            if (service.lower(), creator) == (existing["service"], existing["name"]):
                return existing["id"]
        return False

    def _generate_storage(self):
        for creator in self.creators:
            if not os.path.isfile(f"{creator.name}_{creator.service}.pkl"):
                try:
                    with open(f"{creator.name}_{creator.service}.pkl", "wb") as file:
                        file.write(pickle.dumps(creator.latest()))
                except Exception:
                    Log.yellow(f"Couldn't check Kemono for {creator}.")

    def _hide_console(self):
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32")
        user32 = ctypes.WinDLL("user32")

        SW_HIDE = 0

        hw = kernel32.GetConsoleWindow()

        if hw:
            user32.ShowWindow(hw, SW_HIDE)


def tray_icon(creators: list[Creator]):
    infi.systray.SysTrayIcon(
        ICON,
        "Kemonotify",
        tuple(
            (
                creator.__repr__(),
                None,
                lambda SysTrayIcon: notify(creator, forced=True),
            )
            for creator in creators
        ),
    ).start()


def notify(creator: Creator, forced=False):
    with open(f"{creator.name}_{creator.service}.pkl", "rb+") as file:
        try:
            current = pickle.loads(file.read())
            latest = creator.latest()
            file.write(pickle.dumps(latest))
            if forced:
                send_toast(creator, latest)
                return

            if current != latest:
                Log.white(f"Found a new post on {creator}.")
                send_toast(creator, latest)
        except:
            Log.yellow(f"Couldn't check Kemono for {creator}.")


def send_toast(creator: Creator, latest: dict):
    Log.white(f"Sending notification for {creator}.")

    def _muted(*args):
        pass

    win11toast.toast(
        f"Latest post from {creator}.",
        f"{latest['title']}",
        on_click=lambda args: click(latest),
        app_id="Kemonotify",
        on_dismissed=_muted,
        # icon=IMG + f"/{creator.service.lower()}/{creator.idn}",  ->  Doesn't work for some reason...
    )


def click(latest: dict, **kwargs):
    link = BASE + f"/{latest['service']}/user/{latest['user']}/post/{latest['id']}"
    try:
        webbrowser.open_new(link)
    except:
        Log.yellow(f"Failed to open {link}.")


def checker(creators: list[Creator], time: int):
    while True:
        for creator in creators:
            Log.white(f"Checking {creator}.")
            notify(creator)

        sleep(time)


def main():
    logging.basicConfig(
        filename=LOG,
        level=logging.INFO,
        format="%(levelname)s @ %(asctime)s: %(message)s",
    )
    setup = Setup()
    tray_icon(setup.creators)
    threading.Thread(
        target=checker, args=(setup.creators, setup.time), daemon=True
    ).start()


if __name__ == "__main__":
    threading.Thread(target=main).start()
