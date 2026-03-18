import uvicorn


if __name__ == "__main__":
    uvicorn.run("wsp_autoatt.api.app:app", host="0.0.0.0", port=8000, reload=False)
