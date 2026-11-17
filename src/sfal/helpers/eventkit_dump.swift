// eventkit_dump - read-only EventKit export for SF Activity Log.
// Prints JSON {"status": "...", "events": [...]} for a date window. Recurrences are expanded.
// Usage: eventkit_dump --from YYYY-MM-DD --to YYYY-MM-DD [--source Exchange]
// Exit codes: 0 ok, 2 no calendar access, 3 bad arguments.
import EventKit
import Foundation

func arg(_ name: String) -> String? {
    let a = CommandLine.arguments
    guard let i = a.firstIndex(of: name), i + 1 < a.count else { return nil }
    return a[i + 1]
}

func emit(_ obj: Any, exit code: Int32) -> Never {
    let data = try! JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
    exit(code)
}

let day = DateFormatter()
day.dateFormat = "yyyy-MM-dd"
day.timeZone = .current
guard let fromS = arg("--from"), let toS = arg("--to"),
      let from = day.date(from: fromS), let toDay = day.date(from: toS) else {
    emit(["status": "bad_arguments", "message": "need --from and --to as YYYY-MM-DD"], exit: 3)
}
let to = Calendar.current.date(byAdding: .day, value: 1, to: toDay)!
let sourceFilter = arg("--source")

let store = EKEventStore()
let sem = DispatchSemaphore(value: 0)
var granted = false
store.requestFullAccessToEvents { ok, _ in granted = ok; sem.signal() }
sem.wait()
if !granted {
    emit(["status": "no_access",
          "authorization": EKEventStore.authorizationStatus(for: .event).rawValue,
          "message": "Calendar Full Access not granted. System Settings > Privacy & Security > Calendars > set the app running this tool to Full Access."],
         exit: 2)
}

var calendars = store.calendars(for: .event)
let available = Array(Set(calendars.map { $0.source.title })).sorted()
if let s = sourceFilter {
    calendars = calendars.filter { $0.source.title == s }
    if calendars.isEmpty {
        emit(["status": "source_not_found", "source": s, "available_sources": available,
              "message": "No calendars for source '\(s)'. Add the Exchange account in System Settings > Internet Accounts, or fix sources.calendar.eventkit_source."],
             exit: 2)
    }
}

let iso = ISO8601DateFormatter()
iso.formatOptions = [.withInternetDateTime]
iso.timeZone = .current

func email(_ p: EKParticipant?) -> String {
    guard let u = p?.url.absoluteString else { return "" }
    return u.lowercased().hasPrefix("mailto:") ? String(u.dropFirst(7)) : u
}

func statusName(_ s: EKParticipantStatus) -> String {
    switch s {
    case .accepted: return "accepted"
    case .declined: return "declined"
    case .tentative: return "tentative"
    case .pending: return "pending"
    case .delegated: return "delegated"
    case .completed: return "completed"
    case .inProcess: return "in_process"
    default: return "unknown"
    }
}

let pred = store.predicateForEvents(withStart: from, end: to, calendars: calendars)
let events = store.events(matching: pred).sorted { $0.startDate < $1.startDate }
var out: [[String: Any]] = []
for e in events {
    let attendees: [[String: Any]] = (e.attendees ?? []).map { a in
        ["name": a.name ?? "", "email": email(a), "status": statusName(a.participantStatus),
         "is_me": a.isCurrentUser, "role": a.participantRole.rawValue]
    }
    let me = e.attendees?.first(where: { $0.isCurrentUser })
    let organizerIsMe = e.organizer?.isCurrentUser ?? false
    out.append([
        "external_id": e.calendarItemExternalIdentifier ?? e.eventIdentifier ?? "",
        "start": iso.string(from: e.startDate),
        "end": iso.string(from: e.endDate),
        "all_day": e.isAllDay,
        "title": e.title ?? "",
        "location": e.location ?? "",
        "calendar": e.calendar.title,
        "source": e.calendar.source.title,
        "cancelled": e.status == .canceled,
        "recurring": e.hasRecurrenceRules,
        "organizer": ["name": e.organizer?.name ?? "", "email": email(e.organizer), "is_me": organizerIsMe],
        "my_status": me.map { statusName($0.participantStatus) } ?? (organizerIsMe ? "organizer" : "none"),
        "attendees": attendees,
        "timezone": e.timeZone?.identifier ?? TimeZone.current.identifier,
        "notes": String((e.notes ?? "").prefix(6000)),
        "url": e.url?.absoluteString ?? "",
    ])
}
emit(["status": "ok", "timezone": TimeZone.current.identifier, "available_sources": available,
      "from": fromS, "to": toS, "events": out], exit: 0)
