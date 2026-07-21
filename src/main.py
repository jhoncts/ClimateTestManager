"""Ponto de entrada usado pelo Flet durante desenvolvimento e empacotamento."""

import flet as ft

from climatetest_manager.app import main

if __name__ == "__main__":
    ft.run(main)
