import requests, json, pickle, os, sys, time, logging, infi.systray, threading, win10toast_click, webbrowser


#
# Functions for logging and handling Errors
def err(msg: str):
    logging.error(msg)
    sys.exit(msg)


def warn(msg: str):
    print(msg)
    logging.warning(msg)


def info(msg: str):
    print(msg)
    logging.info(msg)


#
# Function for parsing argv and getting creator info
def parse_argv(c_lst: list[dict], time: int) -> dict:
    arguments = {"time": time, "creators": []}
    for arg in sys.argv[1:]:
        option, value = arg.split("=")
        if option == "time":
            try:
                arguments[option] = int(value)
            except ValueError:
                warn("Defaulted to 1 hour.")
        else:
            try:
                arguments["creators"].append(
                    [
                        creator
                        for creator in c_lst
                        if [creator["service"], creator["name"]] == [option, value]
                    ][0]
                )
            except IndexError:
                warn(f"{option}, {value} not found.")
    if arguments["creators"] == []:
        err("No creators found.")
    return arguments


#
# Function for generating .pkl files for info storage
def generate(api: str, arg: list[dict]):
    for creator in arg:
        if not os.path.isfile(f"{creator['name']}.pkl"):
            with open(f"{creator['name']}.pkl", "wb") as file:
                try:
                    file.write(
                        pickle.dumps(
                            json.loads(
                                requests.get(
                                    api + f"/{creator['service']}/user/{creator['id']}"
                                ).content
                            )[0]
                        )
                    )
                except Exception:
                    err(
                        f"""Couldn't reach {api + f'''/{creator['service']}/user/{creator['id']}'''}."""
                    )

#
# Functions for notification on click
def send_notif(creator: dict, api: str, toast: win10toast_click.ToastNotifier, config: dict):
    with open(f"{creator['name']}.pkl", "rb+") as file:
        try:
            latest = json.loads(
                requests.get(
                    config['api'] + f"/{creator['service']}/user/{creator['id']}"
                ).content
            )[0]
        except Exception:
            err(
                f"""Couldn't reach {config['api'] + f'''/{creator['service']}/user/{creator['id']}'''}."""
            )
        file.write(pickle.dumps(latest))
        toast.show_toast(
            f"Latest post from {creator['name']} on {creator['service']}",
            f"{latest['title']}",
            duration=0,
            icon_path=config['icon'],
            threaded=True,
            callback_on_click=on_click,
            arguments=f"{config['base']}"
                            + f"/{creator['service']}/user/{creator['id']}/post/{latest['id']}"
        )
        
def on_click(link: str):
    try:
        webbrowser.open_new(link)
    except:
        err("Failed to open page.")


#
# The main function
def main():
    with open(os.getcwd()+"/config.json", "rb") as f:
        config = json.loads(f.read())
    logging.basicConfig(filename=config["logging"])
    
    info("Program Started.")

    icon = config["icon"]
    api = config["api"]
    base = config["base"]
    c_lst = json.loads(requests.get(api + "/creators.txt").content)

    toast = win10toast_click.ToastNotifier()

    arguments = parse_argv(c_lst, config["time"])
    generate(api, arguments["creators"])
    
    options = tuple(
        (creator["name"], None, lambda SysTrayIcon: send_notif(creator, api, toast, config)) for creator in arguments["creators"]
    )
    infi.systray.SysTrayIcon(icon, "Kemonotify", options).start()

    def checker():
        while True:
            for creator in arguments["creators"]:
                info(f"Checking {creator['service']}, {creator['name']}.")
                try:
                    latest = json.loads(
                        requests.get(
                            api + f"/{creator['service']}/user/{creator['id']}"
                        ).content
                    )[0]
                except Exception:
                    err(
                        f"""Couldn't reach {api + f'''/{creator['service']}/user/{creator['id']}'''}."""
                    )

                with open(f"{creator['name']}.pkl", "rb+") as file:
                    current = pickle.loads(file.read())
                    if current != latest:
                        info(
                            f"Found {latest['id']} for {creator['service']}, {creator['name']}."
                        )
                        info(
                            f"Link: {base}"
                            + f"/{creator['service']}/user/{creator['id']}/post/{latest['id']}"
                            + "."
                        )
                        
                        file.write(pickle.dumps(latest))

                        toast.show_toast(
                            f"New post from {creator['name']} on {creator['service']}",
                            f"{latest['title']}",
                            duration=0,
                            icon_path=icon,
                            threaded=True,
                            callback_on_click=on_click,
                            arguments=f"Link: {base}"
                            + f"/{creator['service']}/user/{creator['id']}/post/{latest['id']}",
                        )

            # For now just sleep
            time.sleep(arguments["time"])

    threading.Thread(target=checker, daemon=True).start()


if __name__ == "__main__":
    
    threading.Thread(target=main).start()
