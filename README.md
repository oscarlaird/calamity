# Calamity

![Home Image](home.png)

## Installation

Install Calamity via pip:
```
pip install calamity
```

## Overview

Calamity allows you to schedule three types of events:

- **Appointments**: Events with a start and end time.
- **Tasks**: Events with a deadline, like homework.
- **Chores**: Events meant to be performed on the day they're scheduled, such as hygiene tasks.

Events are selected using a coordinate system. Days are chosen with capital letters `A-Z`, and specific events within those days are chosen with numbers `1-9`.

Events can also be repeated daily, weekly, or monthly. Repeated events generally share characteristics like description, color, and time.

## Commands

### Selection & Navigation
- **Day Selection**: `A-Z`
- **Event Selection**: `1-9`
- **Move Down**: `j`
- **Move Up**: `k`
- **Move Right**: `l`
- **Move Left**: `h`
- **Previous Month**: `<`
- **Next Month**: `>`
- **Previous Week**: `b`
- **Next Week**: `w`

### Event Creation
- **Appointment**: `a`
- **Task**: `t`
- **Chore**: `c`

### Event Editing
- **Move Date**: `m`
- **Edit Description**: `d`
- **Edit Time (only for appointments)**: `i`
- **Edit Code (only for tasks)**: `o`
- **Cycle Color**: `;`
- **Cycle Color Backwards**: `,`
- **Delete**: `x`
- **Set Repetition**: `r`
- **Separate Event from a Repetition**: `s`

### Miscellaneous Commands
- **Help**: `?`
- **Undo**: `u`
- **Redo**: `CTRL-R`
- **Cycle through Events**: `TAB`
- **Cycle Appointments**: `SPC`
- **Cycle Tasks**: `RET`
- **First Month**: `gg`
- **Next Month**: `SPC`
- **Previous Month**: `BAC`
- **Quit**: `ESC` or `q`
- **Duplicate Event**: `y`
- **Detach from Recurrence**: `s`

Enjoy scheduling with Calamity!
