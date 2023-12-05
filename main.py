import requests, json, pickle, os, sys, time, logging


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
# The main function
def main():
    info("Program Started.")

    with open("config.json", "rb") as f:
        config = json.loads(f.read())

    logging.basicConfig(filename=config["logging"])
    api = config["api"]
    base = config["base"]
    c_lst = json.loads(requests.get(api + "/creators.txt").content)

    arguments = parse_argv(c_lst, config["time"])
    generate(api, arguments["creators"])

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

        # For now just sleep
        time.sleep(arguments["time"])


if __name__ == "__main__":
    main()