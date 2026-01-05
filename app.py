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
        self.scheduled_times = []

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
        headers_container = ttk.Frame(frame)
        headers_container.grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0))
        headers_container.columnconfigure(0, weight=1)
        self.headers_text = tk.Text(headers_container, height=6, width=60)
        self.headers_text.grid(row=0, column=0, sticky="ew")
        headers_scrollbar = ttk.Scrollbar(headers_container, orient="vertical", command=self.headers_text.yview)
        headers_scrollbar.grid(row=0, column=1, sticky="ns")
        self.headers_text.configure(yscrollcommand=headers_scrollbar.set)

        ttk.Label(frame, text="Cookies (name=value; ...)").grid(row=2, column=0, sticky="nw", pady=(6, 0))
        self.cookies_entry = ttk.Entry(frame)
        self.cookies_entry.grid(row=2, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0))

        ttk.Label(frame, text="Body").grid(row=3, column=0, sticky="nw", pady=(6, 0))
        body_container = ttk.Frame(frame)
        body_container.grid(row=3, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0))
        body_container.columnconfigure(0, weight=1)
        self.body_text = tk.Text(body_container, height=6, width=60)
        self.body_text.grid(row=0, column=0, sticky="ew")
        body_scrollbar = ttk.Scrollbar(body_container, orient="vertical", command=self.body_text.yview)
        body_scrollbar.grid(row=0, column=1, sticky="ns")
        self.body_text.configure(yscrollcommand=body_scrollbar.set)

        self.send_button = ttk.Button(frame, text="Send Request", command=self.send_request_threaded)
        self.send_button.grid(row=4, column=3, sticky="e", pady=6)

    def _build_schedule_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Schedule")
        frame.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        now = datetime.now()
        self.schedule_vars = {
            "hour": tk.IntVar(value=now.hour),
            "minute": tk.IntVar(value=now.minute),
            "second": tk.IntVar(value=now.second),
            "millisecond": tk.IntVar(value=int(now.microsecond / 1000)),
        }

        input_frame = ttk.Frame(frame)
        input_frame.grid(row=0, column=0, sticky="ew")

        ttk.Label(input_frame, text="Hour").grid(row=0, column=0, sticky="w")
        hour_spinbox = ttk.Spinbox(input_frame, from_=0, to=23, width=4, textvariable=self.schedule_vars["hour"])
        hour_spinbox.grid(row=0, column=1, padx=(4, 8))

        ttk.Label(input_frame, text="Minute").grid(row=0, column=2, sticky="w")
        minute_spinbox = ttk.Spinbox(input_frame, from_=0, to=59, width=4, textvariable=self.schedule_vars["minute"])
        minute_spinbox.grid(row=0, column=3, padx=(4, 8))

        ttk.Label(input_frame, text="Second").grid(row=0, column=4, sticky="w")
        second_spinbox = ttk.Spinbox(input_frame, from_=0, to=59, width=4, textvariable=self.schedule_vars["second"])
        second_spinbox.grid(row=0, column=5, padx=(4, 8))

        ttk.Label(input_frame, text="Millisecond").grid(row=0, column=6, sticky="w")
        millisecond_spinbox = ttk.Spinbox(
            input_frame,
            from_=0,
            to=999,
            width=5,
            textvariable=self.schedule_vars["millisecond"],
        )
        millisecond_spinbox.grid(row=0, column=7, padx=(4, 0))

        actions_frame = ttk.Frame(frame)
        actions_frame.grid(row=0, column=1, sticky="e")
        add_button = ttk.Button(actions_frame, text="Add Schedule", command=self.add_schedule_time)
        add_button.grid(row=0, column=0, padx=(0, 6))
        self.schedule_button = ttk.Button(actions_frame, text="Schedule Requests", command=self.schedule_requests)
        self.schedule_button.grid(row=0, column=1)

        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        list_frame.columnconfigure(0, weight=1)

        self.schedule_list = tk.Listbox(list_frame, height=4)
        self.schedule_list.grid(row=0, column=0, sticky="ew")
        schedule_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.schedule_list.yview)
        schedule_scrollbar.grid(row=0, column=1, sticky="ns")
        self.schedule_list.configure(yscrollcommand=schedule_scrollbar.set)

        remove_button = ttk.Button(list_frame, text="Remove Selected", command=self.remove_selected_schedule)
        remove_button.grid(row=1, column=0, sticky="e", pady=(6, 0))

    def _build_response_frame(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Responses")
        frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        self.root.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

        response_list_container = ttk.Frame(frame)
        response_list_container.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        response_list_container.rowconfigure(0, weight=1)
        response_list_container.columnconfigure(0, weight=1)
        self.response_list = tk.Listbox(response_list_container, height=10)
        self.response_list.grid(row=0, column=0, sticky="nsew")
        response_list_scrollbar = ttk.Scrollbar(
            response_list_container,
            orient="vertical",
            command=self.response_list.yview,
        )
        response_list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.response_list.configure(yscrollcommand=response_list_scrollbar.set)
        self.response_list.bind("<<ListboxSelect>>", self.show_response_detail)

        response_detail_container = ttk.Frame(frame)
        response_detail_container.grid(row=0, column=1, sticky="nsew")
        response_detail_container.rowconfigure(0, weight=1)
        response_detail_container.columnconfigure(0, weight=1)
        self.response_detail = tk.Text(response_detail_container, height=10)
        self.response_detail.grid(row=0, column=0, sticky="nsew")
        response_detail_scrollbar = ttk.Scrollbar(
            response_detail_container,
            orient="vertical",
            command=self.response_detail.yview,
        )
        response_detail_scrollbar.grid(row=0, column=1, sticky="ns")
        self.response_detail.configure(yscrollcommand=response_detail_scrollbar.set)

        clear_button = ttk.Button(frame, text="Clear Responses", command=self.clear_responses)
        clear_button.grid(row=1, column=1, sticky="e", pady=(6, 0))

    def schedule_requests(self) -> None:
        if not self.scheduled_times:
            self._append_response("Schedule", "No schedule times provided", "")
            return

        now = datetime.now()
        for schedule_time in self.scheduled_times:
            delay_ms = int((schedule_time - now).total_seconds() * 1000)
            if delay_ms <= 0:
                self._append_response(
                    "Schedule",
                    f"Skipping past time: {schedule_time.strftime('%H:%M:%S.%f')[:-3]}",
                    "",
                )
                continue
            self.root.after(delay_ms, self.send_request_threaded)
            self._append_response(
                "Schedule",
                f"Scheduled request at {schedule_time.strftime('%H:%M:%S.%f')[:-3]}",
                "",
            )

    def send_request_threaded(self) -> None:
        thread = threading.Thread(target=self.send_request, daemon=True)
        thread.start()

    def send_request(self) -> None:
        url = self.url_entry.get().strip()
        method = self.method_var.get().strip().upper()
        body_text = self.body_text.get("1.0", tk.END).rstrip("\n")

        if not url:
            self._append_response("Error", "URL is required", "")
            return

        try:
            headers = parse_headers(self.headers_text.get("1.0", tk.END))
        except ValueError as exc:
            self._append_response("Error", str(exc), "")
            return
        cookies = self.cookies_entry.get().strip()
        if cookies:
            headers["Cookie"] = cookies

        data = body_text.encode("utf-8") if body_text else None
        request = Request(url=url, method=method, headers=headers, data=data)
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8", errors="replace")
                status_line = f"{response.status} {response.reason}"
                response_headers = dict(response.headers.items())
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            status_line = f"HTTPError {exc.code}"
            response_headers = dict(exc.headers.items())
        except URLError as exc:
            body = ""
            status_line = f"URLError {exc.reason}"
            response_headers = {}
        except Exception as exc:
            body = ""
            status_line = f"Error {exc}"
            response_headers = {}

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._append_response(timestamp, status_line, body, response_headers)

    def _append_response(self, title: str, status: str, body: str, headers: dict | None = None) -> None:
        def update_ui() -> None:
            index = len(self.responses) + 1
            label = f"{index}. {title} - {status}"
            self.responses.append({"title": title, "status": status, "body": body, "headers": headers or {}})
            self.response_list.insert(tk.END, label)

        self.root.after(0, update_ui)

    def show_response_detail(self, _event: tk.Event) -> None:
        selection = self.response_list.curselection()
        if not selection:
            return
        response = self.responses[selection[0]]
        self.response_detail.delete("1.0", tk.END)
        self.response_detail.insert(tk.END, f"{response['title']} - {response['status']}\n\n")
        if response["headers"]:
            self.response_detail.insert(tk.END, "Headers:\n")
            for key, value in response["headers"].items():
                self.response_detail.insert(tk.END, f"{key}: {value}\n")
            self.response_detail.insert(tk.END, "\n")
        self.response_detail.insert(tk.END, response["body"])

    def clear_responses(self) -> None:
        self.responses.clear()
        self.response_list.delete(0, tk.END)
        self.response_detail.delete("1.0", tk.END)

    def add_schedule_time(self) -> None:
        now = datetime.now()
        try:
            schedule_time = now.replace(
                hour=int(self.schedule_vars["hour"].get()),
                minute=int(self.schedule_vars["minute"].get()),
                second=int(self.schedule_vars["second"].get()),
                microsecond=int(self.schedule_vars["millisecond"].get()) * 1000,
            )
        except ValueError:
            self._append_response("Schedule", "Invalid schedule time", "")
            return

        self.scheduled_times.append(schedule_time)
        label = schedule_time.strftime("%H:%M:%S.%f")[:-3]
        self.schedule_list.insert(tk.END, label)

    def remove_selected_schedule(self) -> None:
        selection = list(self.schedule_list.curselection())
        if not selection:
            return
        for index in reversed(selection):
            self.schedule_list.delete(index)
            del self.scheduled_times[index]


def main() -> None:
    root = tk.Tk()
    root.geometry("900x600")
    app = HttpMacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
