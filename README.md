# webscraping_app
scrape data 
# WebExtract Pro

A powerful web scraping application designed to extract product data from popular e-commerce platforms in Kenya. Built with Python Flask and featuring specialized scrapers for Jumia and Kilimall.

## 🚀 Features

- **Multi-platform Support**: Scrape data from Jumia and Kilimall
- **Web Interface**: User-friendly web interface for easy interaction
- **Database Integration**: SQLite database for storing scraped data
- **Modular Architecture**: Separate workers for different platforms
- **Real-time Processing**: Live data extraction and processing

## 📋 Requirements

See `requirements.txt` for a complete list of dependencies. Key requirements include:

- Python 3.7+
- Flask
- BeautifulSoup4
- Requests
- SQLite3
- Selenium (for dynamic content)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Dev-pucci/webscraping_app.git
   cd webscraping_app
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python startup.py
   ```

## 🏗️ Project Structure

```
webscraping_app/
│
├── webapp.py              # Main Flask application
├── startup.py             # Application launcher
├── shared_db.py           # Database operations
├── webextract_pro.db      # SQLite database
├── webextract-pro.html    # Main HTML template
├── requirements.txt       # Python dependencies
├── req.MD                 # Requirements documentation
│
├── workers/
│   ├── jumia/
│   │   ├── jumia_scraper.py    # Jumia scraping logic
│   │   ├── jumia_worker.py     # Jumia worker process
│   │   ├── index.html          # Jumia interface
│   │   └── app.js              # Jumia frontend logic
│   │
│   └── kilimall/
│       ├── kilimall_scraper.py     # Kilimall scraping logic
│       ├── kilimall_worker.py      # Kilimall worker process
│       └── kilimall_frontend.html  # Kilimall interface
│
└── __pycache__/           # Python cache files
```

## 🎯 Usage

### Starting the Application
```bash
python startup.py
```

### Accessing the Web Interface
Open your browser and navigate to `http://localhost:5000`

### Scraping Data

#### Jumia Scraper
- Navigate to the Jumia section
- Enter product search terms or categories
- Configure scraping parameters
- Start the scraping process

#### Kilimall Scraper
- Access the Kilimall section
- Set up your scraping preferences
- Monitor the extraction progress

## 🔧 Configuration

The application uses SQLite for data storage. The database file (`webextract_pro.db`) is automatically created when you first run the application.

### Database Schema
The shared database (`shared_db.py`) handles:
- Product information storage
- Scraping session management
- Data persistence and retrieval

## 📊 Scraped Data

The application extracts various product details including:
- Product names and descriptions
- Prices and discounts
- Product images
- Seller information
- Ratings and reviews
- Stock availability

## 🛡️ Best Practices

- **Respect robots.txt**: Always check and follow the website's robots.txt guidelines
- **Rate Limiting**: Implement delays between requests to avoid overwhelming servers
- **Legal Compliance**: Ensure your scraping activities comply with local laws and website terms of service
- **Data Privacy**: Handle scraped data responsibly and in accordance with privacy regulations

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check your Python version compatibility

2. **Database Errors**
   - Verify SQLite is properly installed
   - Check file permissions in the project directory

3. **Scraping Failures**
   - Websites may have changed their structure
   - Check if the target site is accessible
   - Verify your internet connection

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is intended for educational and research purposes. Users are responsible for ensuring their scraping activities comply with:
- Website terms of service
- Local and international laws
- Data protection regulations
- Ethical scraping practices

## 📞 Support

For questions, issues, or contributions, please:
- Open an issue on GitHub
- Contact: officialpucci3@gmail.com

## 🏷️ Version History

- **v1.0.0**: Initial release with Jumia and Kilimall scrapers
- Multi-platform support and web interface

---

**Built with ❤️ by [Dev-pucci](https://github.com/Dev-pucci)**
