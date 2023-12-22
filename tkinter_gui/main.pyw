import os, sys
import requests
import json, pickle
from time import sleep
import logging
import infi.systray, win11toast, webbrowser
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


ONE_HOUR: int = 3600
CWD: str = os.getcwd() + "\\"
BASE: str = "https://kemono.party"
API: str = "https://kemono.party/api/v1"
LOG: str = "logging.log"
ICON: str = "kemono.ico"
IMG: str = "https://img.kemono.su/icons/"
NAME: str = "Kemonotify"
DISPLAY: int = 20
IMG_DIR: str = CWD + "creator_imgs\\"
PKL_DIR: str = CWD + "creator_save\\"


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


class Kemonotify:
    root: tk.Tk
    search: tk.StringVar
    creators_list: list[str]
    last_check: str
    current_checker: dict
    current_display: list[tk.Frame]
    will_check: list[Creator]
    tray: infi.systray.SysTrayIcon
    time: tk.StringVar

    req_thread: threading.Thread

    def __init__(self):
        # GUI
        Log.white("Starting GUI.")
        self.root = tk.Tk()
        self.root.title(NAME)
        self.root.iconbitmap(tk.BitmapImage(ICON))
        self.root.geometry("500x500")
        self.root.resizable = True
        self.root.bind(
            "<Unmap>", lambda Event: None if self.tray == "" else self.root.withdraw()
        )
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.frame_left = tk.Frame(self.root)
        self.frame_left.pack(side=tk.LEFT, expand=tk.TRUE, fill=tk.BOTH, anchor=tk.W)
        self.frame_right = tk.Frame(self.root, border=5)
        self.frame_right.pack(expand=tk.TRUE, fill=tk.BOTH, anchor=tk.N)

        tk.Label(
            self.frame_right,
            text="> CHECKING THESE CREATORS <",
            justify=tk.CENTER,
        ).pack(side=tk.TOP, fill=tk.BOTH, anchor=tk.N)
        self.checking = tk.StringVar()
        tk.Label(self.frame_right, textvariable=self.checking, justify=tk.LEFT).pack(
            side=tk.TOP, fill=tk.BOTH, anchor=tk.N
        )

        self.search_frame = tk.Frame(self.frame_left)
        self.search_frame.pack(fill=tk.X, anchor=tk.N)

        tk.Label(self.search_frame, text="Search:").pack(side=tk.LEFT)
        self.search = tk.StringVar()
        self.last_check = self.search.get()
        self.entry = ttk.Entry(self.search_frame, textvariable=self.search)
        self.entry.pack(side=tk.LEFT, expand=tk.TRUE, fill=tk.X)
        

        self.time = tk.StringVar()
        ttk.Entry(self.search_frame, textvariable=self.time, width=10).pack(
            side=tk.RIGHT
        )
        tk.Label(self.search_frame, text="Time:").pack(side=tk.RIGHT)

        self.frame_list = tk.Frame(self.frame_left)
        self.frame_list.pack(expand=tk.TRUE, fill=tk.BOTH, anchor=tk.N)

        self.scrollbar = tk.Scrollbar(self.frame_list)
        self.scrollbar.pack(side=tk.RIGHT, expand=tk.FALSE, fill=tk.Y, anchor=tk.N)

        self.canvas = tk.Canvas(
            self.frame_list,
            bd=0,
            highlightthickness=0,
            yscrollcommand=self.scrollbar.set,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE, anchor=tk.N)

        self.scrollbar.config(command=self.canvas.yview)

        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        self.interior = tk.Frame(self.canvas)
        self.int_id = self.canvas.create_window(
            0, 0, window=self.interior, anchor=tk.NW
        )
        self.interior.bind("<Configure>", self._configure_interior)
        self.canvas.bind("<Configure>", self._configure_canvas)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # self.placeholder = tk.Label(self.interior, text="PRESS <ENTER> TO SEARCH")
        # self.placeholder.pack()

        self._hold_img = (
            []
        )  # There's a tk bug that requires the images to be held like this to display

        # Program
        Log.white("Starting program.")
        self._verify_dir()
        self._setup_logging()
        self.tray = ""
        self.tray = self._start_sys_tray()

        self.creators_list = self._get_creators_list()

        self.current_checker = []
        self.will_check = []
        # threading.Thread(target=self.handler, daemon=True).start()
        self.entry.bind("<Return>", self.handler)
        self.req_thread = threading.Thread(target=self._check_creators, daemon=True)

        self.root.mainloop()

    def _verify_dir(self):
        if not os.path.isdir(PKL_DIR):
            os.makedirs(PKL_DIR)
        if not os.path.isdir(IMG_DIR):
            os.makedirs(IMG_DIR)

    def on_closing(self):
        self.root.destroy()
        try:
            self.tray.shutdown()
        except:
            return

    def _configure_interior(self, event):
        size = self.interior.winfo_reqwidth(), self.interior.winfo_reqheight()
        self.canvas.config(scrollregion=f"0 0 {size[0]} {size[1]}")
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            self.canvas.config(width=self.interior.winfo_reqwidth())

    def _configure_canvas(self, event):
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            self.canvas.itemconfigure(self.int_id, width=self.canvas.winfo_width())

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _setup_logging(self):
        logging.basicConfig(
            filename=LOG,
            level=logging.INFO,
            format="%(levelname)s @ %(asctime)s: %(message)s",
        )

    def _start_sys_tray(self, options=()):
        deicon = ((f"Open {NAME}", None, lambda SysTrayIcon: self.root.deiconify()),)
        if self.tray != "":
            self.tray.shutdown()
        tray = infi.systray.SysTrayIcon(
            ICON,
            NAME,
            deicon + options,
            on_quit=lambda SysTrayIcon: self._make_empty(),
        )
        tray.start()
        return tray
    
    def _make_empty(self):
        self.tray = ""

    def _get_creators_list(self):
        try:
            _temp = json.loads(requests.get(API + "/creators.txt").content)
            return sorted(
                _temp,
                key=lambda d: d["favorited"],
                reverse=True,
            )
            Log.white("Got Creators List.")
        except:
            Log.red(f"Couldn't get creators list.")

    def handler(self, event):
        # while True:
        #     if self.search.get() == self.last_check:
        #         pass
        #     else:
        #         self.last_check = self.search.get()
        #         self._display_creators()
        self.last_check = self.search.get()
        self._display_creators()

    def _display_creators(self):
        self._clear_display()

        creators = self._get_creators()
        Log.white(f"Got creators based on: {self.last_check}")

        self._generate_imgs(creators)
        Log.white("Finished getting images.")

        self.current_checker = self._pack_creators_get_state(creators)
        Log.white("Got states and frames.")

        self._update_wanted()

    def _clear_display(self):
        for frame in self.interior.slaves():
            frame.destroy()
        Log.white("Cleared display.")

    def _get_creators(self) -> list[Creator]:
        return [
            Creator(creator["service"], creator["name"], creator["id"])
            for creator in [
                creator
                for creator in self.creators_list
                if self.search.get() in creator["name"]
            ][:DISPLAY]
        ]

    def _generate_imgs(self, creators: list[Creator]):
        Log.white("Generating images.")
        try:
            for creator in creators:
                if os.path.isfile(IMG_DIR + f"{creator.idn}.png"):
                    continue
                with open(IMG_DIR + f"{creator.idn}.png", "wb") as img_file:
                    img_file.write(
                        requests.get(IMG + f"{creator.service}/{creator.idn}").content
                    )
        except:
            Log.yellow("Couldn't reach Kemono IMG server.")

    def _pack_creators_get_state(
        self, creators: list[Creator]
    ) -> (dict, list[tk.Frame]):
        self._hold_img = []
        _to_pack = {}
        _frames = []
        _imgs = []
        # self.placeholder.destroy()
        for creator in creators:
            _to_pack.update({creator: tk.BooleanVar()})
            _frames.append(tk.Frame(self.interior))
            if os.path.isfile(IMG_DIR + f"{creator.idn}.png"):
                try:
                    _imgs.append(
                        ImageTk.PhotoImage(
                            Image.open(IMG_DIR + f"{creator.idn}.png").resize(
                                (100, 100)
                            )
                        )
                    )
                    tk.Label(
                        _frames[-1],
                        image=_imgs[-1],
                        anchor=tk.W,
                    ).grid(column=0, row=0)
                except:
                    Log.yellow(f"Image couldn't be loaded for {creator}.")
                    pass
            tk.Label(_frames[-1], text=creator.__repr__(), anchor=tk.W, width=20).grid(
                column=1, row=0
            )
            tk.Checkbutton(
                _frames[-1],
                anchor=tk.W,
                command=self._check_wanted,
                variable=_to_pack[creator],
            ).grid(column=2, row=0)
            _frames[-1].pack()

        for creator in _to_pack:
            if creator.idn in [c.idn for c in self.will_check]:
                _to_pack[creator].set(tk.TRUE)

        self._hold_img = _imgs  # Aforementioned bug
        return _to_pack

    def _check_wanted(self):
        for creator in self.current_checker:
            if creator.idn in [c.idn for c in self.will_check]:
                if not self.current_checker[creator].get():
                    self.will_check = [
                        c for c in self.will_check if creator.idn != c.idn
                    ]
                continue
            if self.current_checker[creator].get():
                self.will_check.append(creator)

        self._generate_storage()
        if not self.req_thread.is_alive():
            self.req_thread.start()

        self.tray = self._start_sys_tray(
            options=tuple(
                (
                    creator.__repr__(),
                    None,
                    lambda SysTrayIcon: self.notify(creator, forced=True),
                )
                for creator in self.will_check
            )
        )
        self._update_wanted()

    def _generate_storage(self):
        for creator in self.will_check:
            if not os.path.isfile(f"{PKL_DIR}{creator.idn}.pkl"):
                try:
                    with open(f"{PKL_DIR}{creator.idn}.pkl", "wb") as file:
                        file.write(pickle.dumps(creator.latest()))
                except Exception:
                    Log.yellow(f"Couldn't check Kemono for {creator}.")

    def _update_wanted(self):
        self.checking.set(
            "\n".join([creator.__repr__() for creator in self.will_check])
        )
        if self.checking.get() == "":
            self.checking.set("NO CREATOR SELECTED.")

    def _check_creators(self):
        while True:
            try:
                _time = int(self.time.get())
            except:
                _time = ONE_HOUR

            for creator in self.will_check:
                Log.white(f"Checking {creator}.")
                threading.Thread(
                    target=self.notify, args=[creator], daemon=True
                ).start()

            self.time.set(_time)
            sleep(_time)

    def notify(self, creator: Creator, forced=False):
        with open(f"{PKL_DIR}{creator.idn}.pkl", "rb+") as file:
            try:
                current = pickle.loads(file.read())
                latest = creator.latest()
                file.write(pickle.dumps(current))
                if forced:
                    self.send_toast(creator, latest)
                    return

                if current != latest:
                    Log.white(f"Found a new post on {creator}.")
                    self.send_toast(creator, latest)
            except:
                Log.yellow(f"Couldn't check Kemono for {creator}.")

    def send_toast(self, creator: Creator, latest: dict):
        Log.white(f"Sending notification for {creator}.")

        def _muted(*args):
            pass

        win11toast.toast(
            f"Latest post from {creator}.",
            f"{latest['title']}",
            on_click=lambda args: self.click(latest),
            app_id=NAME,
            on_dismissed=_muted,
        )

    def click(self, latest: dict, **kwargs):
        link = BASE + f"/{latest['service']}/user/{latest['user']}/post/{latest['id']}"
        try:
            webbrowser.open_new(link)
        except:
            Log.yellow(f"Failed to open {link}.")


if __name__ == "__main__":
    kemonotify = Kemonotify()
