

if __name__ == "__main__":
    import webui

    debug = False
    app = webui.App("iot.boop.li")

    app.Server.run(host="::", port=8083, debug=debug, reloader=debug, server="paste")


