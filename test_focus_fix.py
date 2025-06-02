#!/usr/bin/env python3
"""
Test script to verify that the focus fix works correctly.

This script tests:
1. Tab key functionality still works (switches focus between search and table)
2. Arrow key navigation still selects items when navigating
3. Focus method no longer automatically selects first item
4. Double-click and space key still work for opening links
"""

import tkinter as tk
from tkinter import ttk
from ui.components.link_list_view import LinkListView
from ui.components.search_bar import SearchBar
from models.link import Link
from datetime import datetime

class TestApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Focus Fix Test")
        self.root.geometry("800x600")
        
        # Create test data
        self.test_links = [
            Link("Test Link 1", "https://example1.com", False, datetime.now(), None),
            Link("Test Link 2", "https://example2.com", True, datetime.now(), None),
            Link("Test Link 3", "https://example3.com", False, datetime.now(), datetime.now()),
        ]
        
        self.create_ui()
        self.setup_callbacks()
        
    def create_ui(self):
        # Main container
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Search bar
        self.search_bar = SearchBar(container)
        
        # Link list view
        list_container = tk.Frame(container)
        list_container.pack(fill=tk.BOTH, expand=True)
        self.link_list_view = LinkListView(list_container)
        
        # Set initial data
        self.link_list_view.set_links(self.test_links, self.test_links)
        
        # Test buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(btn_frame, text="Test Focus", command=self.test_focus).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear Selection", command=self.clear_selection).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Check Selection", command=self.check_selection).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(self.root, text="Ready for testing", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Bind Tab key
        self.root.bind("<Tab>", self.on_tab_pressed)
        
    def setup_callbacks(self):
        self.link_list_view.set_double_click_callback(self.on_double_click)
        self.link_list_view.set_space_key_callback(self.on_space_key)
        
    def test_focus(self):
        """Test focus behavior - should NOT automatically select first item"""
        self.status_label.config(text="Testing focus() method...")
        self.link_list_view.clear_selection()
        self.link_list_view.focus()
        
        # Check if anything was selected
        selection = self.link_list_view.get_selected_indices()
        if selection:
            self.status_label.config(text=f"FAIL: focus() auto-selected item(s): {selection}")
        else:
            self.status_label.config(text="PASS: focus() did not auto-select any items")
            
    def clear_selection(self):
        """Clear selection for testing"""
        self.link_list_view.clear_selection()
        self.status_label.config(text="Selection cleared")
        
    def check_selection(self):
        """Check current selection"""
        selection = self.link_list_view.get_selected_indices()
        self.status_label.config(text=f"Current selection: {selection}")
        
    def on_tab_pressed(self, event):
        """Handle Tab key to switch focus"""
        if self.search_bar.has_focus():
            self.link_list_view.focus()
            self.status_label.config(text="Focus switched to table")
        else:
            self.search_bar.focus()
            self.status_label.config(text="Focus switched to search")
        return "break"
        
    def on_double_click(self, indices):
        """Handle double-click"""
        self.status_label.config(text=f"Double-clicked on items: {indices}")
        
    def on_space_key(self):
        """Handle space key"""
        selection = self.link_list_view.get_selected_indices()
        self.status_label.config(text=f"Space pressed on items: {selection}")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    print("Focus Fix Test")
    print("==============")
    print("1. Click 'Test Focus' - should show PASS (no auto-selection)")
    print("2. Press Tab to switch focus - should work normally")
    print("3. Use arrow keys to navigate - should select items")
    print("4. Double-click items - should work normally")
    print("5. Select items and press space - should work normally")
    print("")
    
    app = TestApp()
    app.run() 