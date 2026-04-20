import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock supabase before importing tgpc package modules
sys.modules["supabase"] = MagicMock()

from tgpc.utils import Config
from tgpc.scraper import Scraper


def make_response(html: str) -> MagicMock:
    response = MagicMock()
    response.content = html.encode("utf-8")
    response.text = html
    return response


class ScraperParsingTests(unittest.TestCase):
    def test_request_uses_split_connect_and_read_timeouts(self):
        scraper = Scraper()
        response = MagicMock()
        response.status_code = 200
        response.text = "ok" * 1000
        response.raise_for_status.return_value = None

        with patch.object(scraper.rate_limiter, "wait"), patch.object(
            scraper.rate_limiter, "record_result"
        ) as record_result, patch.object(
            scraper.session, "request", return_value=response
        ) as request_mock:
            result = scraper._request("GET", "https://example.com")

        self.assertIs(result, response)
        request_mock.assert_called_once_with(
            "GET",
            "https://example.com",
            timeout=(scraper.config.connect_timeout, scraper.config.read_timeout),
        )
        record_result.assert_called_once_with(True)

    def test_extract_basic_records_falls_back_to_first_table_and_skips_bad_rows(self):
        html = """
        <html>
        <body>
            <table>
                <tr>
                    <th>S.No</th><th>Reg No</th><th>Name</th><th>Father Name</th><th>Category</th>
                </tr>
                <tr>
                    <td>BAD</td><td>RX001</td><td>Alice</td><td>Parent One</td><td>BPharm</td>
                </tr>
                <tr>
                    <td>2</td><td>RX002</td><td>Bob</td><td>Parent Two</td>
                </tr>
                <tr>
                    <td>3</td><td>RX003</td><td>Carol</td><td>Parent Three</td><td>DPharm</td><td>Ignored</td>
                </tr>
            </table>
        </body>
        </html>
        """

        scraper = Scraper()
        with patch.object(scraper, "_request", return_value=make_response(html)):
            records = scraper.extract_basic_records()

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].registration_number, "RX001")
        self.assertIsNone(records[0].serial_number)
        self.assertEqual(records[1].registration_number, "RX003")
        self.assertEqual(records[1].serial_number, 3)

    def test_extract_basic_records_returns_empty_when_no_table_exists(self):
        scraper = Scraper()
        with patch.object(scraper, "_request", return_value=make_response("<html><body>No table</body></html>")):
            records = scraper.extract_basic_records()

        self.assertEqual(records, [])

    def test_extract_detailed_info_returns_none_for_no_records_found(self):
        scraper = Scraper()
        with patch.object(scraper, "_request", return_value=make_response("<html><body>No Records Found</body></html>")):
            record = scraper.extract_detailed_info("RX404")

        self.assertIsNone(record)

    def test_extract_detailed_info_parses_validity_education_and_photo(self):
        html = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Registration No</th>
                    <th>Name</th>
                    <th>Father Name</th>
                    <th>Gender</th>
                    <th>Validity</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Photo</th>
                </tr>
                <tr>
                    <td>RX123</td>
                    <td>Jane Pharmacist</td>
                    <td>Parent Name</td>
                    <td>Female</td>
                    <td>31/12/2026</td>
                    <td>BPharm</td>
                    <td>Active</td>
                    <td><img id="imgPhotoMain" src="data:image/jpeg;base64,QUJDREVGRw==" /></td>
                </tr>
            </table>
            <table>
                <tr>
                    <th>Category</th><th>Board/University</th><th>College Name</th><th>College Address</th><th>From</th><th>To</th><th>HT No</th>
                </tr>
                <tr>
                    <th>BPharm</th><td>Osmania University</td><td>City College</td><td>Hyderabad</td><td>2014</td><td>2018</td><td>HT123</td>
                </tr>
                <tr>
                    <th>MPharm</th><td>Kakatiya University</td><td>North Campus</td><td>Warangal</td><td>2019</td><td></td><td></td>
                </tr>
            </table>
            <table>
                <tr>
                    <th>Address</th><th>State</th><th>District</th><th>Pin code</th>
                </tr>
                <tr>
                    <td>Clinic Street</td><td>Telangana</td><td>Hyderabad</td><td>500001</td>
                </tr>
            </table>
        </body>
        </html>
        """

        scraper = Scraper()
        with patch.object(scraper, "_request", return_value=make_response(html)):
            record = scraper.extract_detailed_info("RX123")

        self.assertIsNotNone(record)
        self.assertEqual(record.registration_number, "RX123")
        self.assertEqual(record.name, "Jane Pharmacist")
        self.assertEqual(record.father_name, "Parent Name")
        self.assertEqual(record.category, "BPharm")
        self.assertEqual(record.validity_date, "31/12/2026")
        self.assertEqual(record.photo_base64, "QUJDREVGRw==")
        self.assertEqual(
            record.education,
            [
                {
                    "Category": "BPharm",
                    "Board/University": "Osmania University",
                    "year": "2018",
                    "College Name": "City College",
                    "College Address": "Hyderabad",
                    "from": "2014",
                    "to": "2018",
                    "hall_ticket_number": "HT123",
                },
                {
                    "Category": "MPharm",
                    "Board/University": "Kakatiya University",
                    "year": "",
                    "College Name": "North Campus",
                    "College Address": "Warangal",
                    "from": "2019",
                    "to": "",
                    "hall_ticket_number": "",
                },
            ],
        )
        self.assertEqual(
            record.work_experience,
            {
                "address": "Clinic Street",
                "state": "Telangana",
                "district": "Hyderabad",
                "pin_code": "500001",
            },
        )

    def test_extract_detailed_info_supports_legacy_education_headers(self):
        html = """
        <html>
        <body>
            <table>
                <tr>
                    <th>S.No</th><th>Qualification</th><th>University</th><th>Year</th>
                </tr>
                <tr>
                    <td>1</td><td>B.Pharm</td><td>Osmania University</td><td>2018</td>
                </tr>
                <tr>
                    <td>2</td><td>M.Pharm</td><td>Kakatiya University</td>
                </tr>
            </table>
        </body>
        </html>
        """

        scraper = Scraper()
        with patch.object(scraper, "_request", return_value=make_response(html)):
            record = scraper.extract_detailed_info("RX123")

        self.assertIsNotNone(record)
        self.assertEqual(
            record.education,
            [
                {
                    "Category": "B.Pharm",
                    "Board/University": "Osmania University",
                    "year": "2018",
                    "College Name": "",
                    "College Address": "",
                    "from": "",
                    "to": "",
                    "hall_ticket_number": "",
                },
                {
                    "Category": "M.Pharm",
                    "Board/University": "Kakatiya University",
                    "year": "",
                    "College Name": "",
                    "College Address": "",
                    "from": "",
                    "to": "",
                    "hall_ticket_number": "",
                },
            ],
        )

    def test_extract_detailed_info_returns_none_when_tables_are_missing(self):
        html = "<html><body><div>Valid Upto : 31-12-2026</div></body></html>"

        scraper = Scraper()
        with patch.object(scraper, "_request", return_value=make_response(html)):
            record = scraper.extract_detailed_info("RX321")

        self.assertIsNone(record)


if __name__ == "__main__":
    unittest.main()
