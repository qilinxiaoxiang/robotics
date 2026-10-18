# MicroDuck bring-up logbook

Problem IDs P5 (serviceable hardware) and P6 (reliable deployment). This folder is the working record of the bench-first bring-up that started on 2026-10-10. One file per day. Each day has a goal, the industry step it corresponds to, the software used, the checks that define success, and the measurements taken. Measurements recorded here are the source of truth for later CAD changes; a CAD number that disagrees with a caliper number loses.

## Rules for this phase

- Nothing is soldered in the harness. Every connection is a plug, a screw terminal or a lever connector. The only soldering is a header onto a breakout board, done once by a helper.
- Every subsystem is tested alone on the bench before it goes into a printed part.
- A printed part is reprinted only after the real connector has been measured on the real board.
- Every number comes from a caliper or a meter and is written here with the date.

## The loop and where it comes from

The standard sequence for building or replicating a small robot is: block diagram, bill of materials, CAD with the real component models, print, bench bring-up of each subsystem, integration, test, documentation. The bench bring-up step is what hardware teams call bring-up; the print and fit loop is what they call EVT (engineering validation) on a one-person scale. The software that carries each step:

- Block diagram and wire list: a spreadsheet (from pin, to pin, wire, connector) or KiCad for a drawn schematic.
- Mechanical CAD: Onshape (the upstream duck family is designed in Onshape), Fusion 360 or SolidWorks. Component models come from the manufacturer or GrabCAD as STEP files.
- Slicing: Bambu Studio or OrcaSlicer.
- Servo setup: DYNAMIXEL Wizard 2.0 (ROBOTIS), with the OpenRB-150 as the USB to DYNAMIXEL bridge.
- Pi setup: Raspberry Pi Imager, then ssh.
- Measurement: digital caliper, multimeter.

## Days

- [Day 1: bench connection and measurements](day1-bench.md)
