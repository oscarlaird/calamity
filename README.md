# Calamity

## Calamity is a terminal-based calendar focused on fast navigation, fast data-entry, and vim-like bindings.

![Home Image](home.png)

## Installation

Install Calamity via pip:
```
>>> pip install calamity_calendar
>>> calamity
```

Your calendar is stored in `~/.local/share/calamity/events.db`.

## Usage

- **Three kinds of events**: appointments, tasks, and chores.
    - **Appointments**: start time and end time.
    - **Tasks**: have a deadline (e.g. homework).
    - **Chores**: performed on the day they're scheduled (e.g. hygiene)

- **Selection**:
    - **Coordinate system**: Day (`A-Z`), Event (`1-9`).
    - **Vim motions** (e.g. `j`, `k`, `h`, `l`) to navigate.

- **Repetitions (Groups)**:
    - `r` Create repetitions. (`r` followed by 7+13 creates 13 weekly repetitions.)
    - Individual events are edited with with the `e` prefix.
    - Entire repetition groups are edited with the `g` prefix.


### New Event
| Command | Description |
| ------- | ----------- |
| `a` | Appointment |
| `t` | Task |
| `c` | Chore |

### Selection
| Command | Description |
|---------| ----------- |
| `A-Z`     | Day |
| `1-9`     | Event |
| `j  `     | Down |
| `k  `     | Up |
| `l  `     | Right (Event) |
| `h  `     | Left (Event) |
| `\> `     | Next month |
| `<  `     | Previous month |
| `w  `     | Next week |
| `b  `     | Previous week |
| `TAB`     | Next chore |
| `SPC`     | Next appointment |
| `RET`     | Next task |
| `gg `     | Jump to today |

### Edit
| Edit Event | Edit Repetition Group | Description |
|----------|-----------------------|-----------------------------------|
| `eD`       | `N/A`                  | Edit date                         |
| `ed`       | `gd `                  | Edit description                  |
| `ec`       | `gc `                  | Edit code (task)                  |
| `es`       | `gs `                  | Edit start time (appointment)     |
| `ef`       | `gf `                  | Edit finish time (appointment)    |
| `et`       | `gt `                  | Edit time (appointment)           |
| `; `       | `g; `                   | Cycle color forwards              |
| `, `       | `g, `                   | Cycle color backwards             |
| `+ `       | `g+ `                   | Postpone one day                  |
| `- `       | `g- `                   | Prepone one day                   |
| `x `       | `gx `                   | Delete event                      |
| `r `       | `gr `                   | Repeat event                      |
| `m `       | `gm `                   | Move event                        |
| `~ `       | `g~ `                   | Toggle chore / task               |
| `gX`       | `N/A`                | Kill future repetitions           |

### Undo
| Command | Description |
| ------- | ----------- |
| `u` | Undo |
| `CTRL-R` | Redo |
| `.` | Repeat last action |


### Search
| Command | Description |
| ------- | ----------- |
| `/` | Search |
| `n` | Next match |
| `N` | Previous match |
| `*` | Next repetition |
| `#` | Previous repetition |

### Miscellaneous
| Command | Description                          |
| ------- |--------------------------------------|
| `y` | Yank event                         |
| `gy` | Yank repetition group              |
| `p `| Paste yanked event/group             |
| `s `| Separate event from repetition group |
| `v `| Backup calendar                      |
| `q `| Quit                                 |

### View
| Command | Description |
| ------- | ----------- |
| `zk` | Up |
| `zj` | Down |
| `zh` | Left |
| `zl` | Right |
| `zz` | Center |
| `zt` | Top |
| `zb` | Bottom |
| `z0` | Toggle 12/24 hour |
| `z?` | Toggle help visibility |
| `g!` | Toggle ROT13 encryption |

---


