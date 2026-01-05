import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SUPPORTED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def parse_headers(raw_headers: str) -> dict:
    headers = {}
    for line in raw_headers.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"Invalid header line: {line}")
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


class HttpMacroApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("HTTP Macro")
        self.responses = []

        self._build_request_frame()
        self._build_schedule_frame()
        self._build_response_frame()

    def _build_request_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Request")
        frame.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="URL").grid(row=0, column=0, sticky="w")
        self.url_entry = ttk.Entry(frame)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=6)

        ttk.Label(frame, text="Method").grid(row=0, column=2, sticky="w")
        self.method_var = tk.StringVar(value=SUPPORTED_METHODS[0])
        self.method_menu = ttk.OptionMenu(frame, self.method_var, SUPPORTED_METHODS[0], *SUPPORTED_METHODS)
        self.method_menu.grid(row=0, column=3, sticky="w")

        ttk.Label(frame, text="Headers (key: value)").grid(row=1, column=0, sticky="nw", pady=(6, 0))
        self.headers_text = tk.Text(frame, height=6, width=60)
        self.headers_text.grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0))

        self.send_button = ttk.Button(frame, text="Send Request", command=self.send_request_threaded)
        self.send_button.grid(row=2, column=3, sticky="e", pady=6)

    def _build_schedule_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Schedule")
        frame.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Times (ms, comma-separated)").grid(row=0, column=0, sticky="w")
        self.schedule_entry = ttk.Entry(frame)
        self.schedule_entry.grid(row=0, column=1, sticky="ew", padx=6)

        self.schedule_button = ttk.Button(frame, text="Schedule Requests", command=self.schedule_requests)
        self.schedule_button.grid(row=0, column=2, sticky="e")

    def _build_response_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Responses")
        frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        self.root.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

        self.response_list = tk.Listbox(frame, height=10)
        self.response_list.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.response_list.bind("<<ListboxSelect>>", self.show_response_detail)

        self.response_detail = tk.Text(frame, height=10)
        self.response_detail.grid(row=0, column=1, sticky="nsew")

    def schedule_requests(self) -> None:
        raw = self.schedule_entry.get()
        if not raw.strip():
            self._append_response("Schedule", "No schedule times provided", "")
            return
        try:
            delays = [int(item.strip()) for item in raw.replace(";", ",").split(",") if item.strip()]
        except ValueError:
            self._append_response("Schedule", "Invalid schedule time", "")
            return

        for delay_ms in delays:
            if delay_ms < 0:
                self._append_response("Schedule", f"Skipping negative delay: {delay_ms}ms", "")
                continue
            self.root.after(delay_ms, self.send_request_threaded)
            self._append_response("Schedule", f"Scheduled request in {delay_ms}ms", "")

    def send_request_threaded(self) -> None:
        thread = threading.Thread(target=self.send_request, daemon=True)
        thread.start()

    def send_request(self) -> None:
        url = self.url_entry.get().strip()
        method = self.method_var.get().strip().upper()

        if not url:
            self._append_response("Error", "URL is required", "")
            return

        try:
            headers = parse_headers(self.headers_text.get("1.0", tk.END))
        except ValueError as exc:
            self._append_response("Error", str(exc), "")
            return

        request = Request(url=url, method=method, headers=headers)
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8", errors="replace")
                status_line = f"{response.status} {response.reason}"
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            status_line = f"HTTPError {exc.code}"
        except URLError as exc:
            body = ""
            status_line = f"URLError {exc.reason}"
        except Exception as exc:
            body = ""
            status_line = f"Error {exc}"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._append_response(timestamp, status_line, body)

    def _append_response(self, title: str, status: str, body: str) -> None:
        def update_ui() -> None:
            index = len(self.responses) + 1
            label = f"{index}. {title} - {status}"
            self.responses.append({"title": title, "status": status, "body": body})
            self.response_list.insert(tk.END, label)

        self.root.after(0, update_ui)

    def show_response_detail(self, _event: tk.Event) -> None:
        selection = self.response_list.curselection()
        if not selection:
            return
        response = self.responses[selection[0]]
        self.response_detail.delete("1.0", tk.END)
        self.response_detail.insert(tk.END, f"{response['title']} - {response['status']}\n\n")
        self.response_detail.insert(tk.END, response["body"])


def main() -> None:
    root = tk.Tk()
    root.geometry("900x600")
    app = HttpMacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
