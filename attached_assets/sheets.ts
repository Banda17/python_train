import { google } from 'googleapis';
import { JWT } from 'google-auth-library';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Initialize auth client
const credentialsPath = path.resolve(process.cwd(), 'nimble-willow-433310-n1-f8d544889cfe.json');
console.log('Loading credentials from:', credentialsPath);

let credentials;
try {
  credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
  console.log('Successfully loaded credentials for:', credentials.client_email);
} catch (error) {
  console.error('Error loading credentials:', error);
  throw new Error('Failed to load service account credentials');
}

// Configure JWT auth client with service account
const auth = new JWT({
  email: credentials.client_email,
  key: credentials.private_key,
  scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
});

// Initialize Google Sheets API
const sheets = google.sheets({ version: 'v4', auth });
console.log('Google Sheets API initialized');

// Default spreadsheet configuration from the service account
const DEFAULT_SPREADSHEET_ID = '1OuiQ3FEoNAtH10NllgLusxACjn2NU0yZUcHh68hLoI4';
const DEFAULT_RANGE = 'Sheet1!A1:L';

interface SheetData {
  values: any[][];
  headers: string[];
}

export async function fetchSheetData(spreadsheetId: string = DEFAULT_SPREADSHEET_ID, range: string = DEFAULT_RANGE): Promise<SheetData> {
  console.log(`Attempting to fetch sheet data from spreadsheet: ${spreadsheetId}, range: ${range}`);
  
  if (!spreadsheetId || !range) {
    console.error('Missing required parameters:', { spreadsheetId, range });
    throw new Error('Spreadsheet ID and range are required');
  }

  try {
    console.log('Making API request to Google Sheets...');
    
    // First verify access to the spreadsheet
    const metadata = await sheets.spreadsheets.get({
      spreadsheetId,
      fields: 'properties.title'
    });
    
    console.log('Successfully accessed spreadsheet:', metadata.data.properties?.title);

    // Now fetch the actual data
    const response = await sheets.spreadsheets.values.get({
      spreadsheetId,
      range,
      valueRenderOption: 'UNFORMATTED_VALUE',
      dateTimeRenderOption: 'FORMATTED_STRING',
    });

    const values = response.data.values;
    if (!values || values.length === 0) {
      console.error('No data found in spreadsheet');
      throw new Error('No data found in the spreadsheet');
    }

    // Define headers for the sheet data
    const headers = [
      'timestamp',
      '',           // empty column
      'BD No',
      'Sl No',
      'Train Name',
      'LOCO',
      'Station',
      'Status',
      'Time',
      'Remarks',
      'FOISID',
      'uid'
    ];

    console.log('Processing sheet values:', values);

    // Start from row A3 (index 2 in the array) and map the data
    // Get raw data rows, starting from row 3 (index 2)
    const rows = values.slice(2);
    
    // Transform each row into the expected format
    const transformedData = rows.map(row => {
      const transformedRow = {
        timestamp: row[0] || '',
        emptyColumn:row[1],
        'BD No': row[2] || '',
        'Sl No': row[3] || '',
        'Train Name': row[4] || '',
        'LOCO': row[5] || '',
        'Station': row[6] || '',
        'Status': row[7] || '',
        'Time': row[8] || '',
        'Remarks': row[9] || '',
        'FOISID': row[10] || '',
        'uid': row[11] || ''
      };
      return transformedRow;
    }).filter(row => Object.values(row).some(value => value !== '')); // Filter out empty rows

    // Filter out any empty or invalid rows
    const validData = transformedData.filter(row => 
      Object.values(row).some(value => value !== undefined && value !== '')
    );

    const returnData: SheetData = {
      values: validData as any[],
      headers: headers
    };

    console.log('Transformed data structure:', returnData);
    return returnData;
  } catch (error: any) {
    console.error('Error fetching sheet data:', error);
    
    // Handle specific Google API errors
    if (error.code === 403) {
      console.error('Access denied error:', error.message);
      throw new Error('Access denied. Please ensure the service account has access to the spreadsheet.');
    }
    if (error.code === 404) {
      console.error('Not found error:', error.message);
      throw new Error('Spreadsheet not found. Please verify the spreadsheet ID.');
    }
    if (error.response?.data?.error) {
      console.error('Google API error:', error.response.data.error);
      throw new Error(`Google Sheets API error: ${error.response.data.error.message}`);
    }
    
    throw new Error(`Failed to fetch sheet data: ${error.message}`);
  }
}

interface DataTransformer {
  toJSON(): Record<string, any>[];
  toCSV(): string;
  filter(predicate: (row: Record<string, any>) => boolean): DataTransformer;
  map(transform: (row: Record<string, any>) => Record<string, any>): DataTransformer;
}

export class SheetDataTransformer implements DataTransformer {
  private data: Record<string, any>[];

  constructor(sheetData: SheetData) {
    if (!sheetData || !Array.isArray(sheetData.values)) {
      console.error('Invalid sheet data received:', sheetData);
      this.data = [];
      return;
    }
    
    // Filter out any empty or invalid rows
    this.data = sheetData.values.filter(row => 
      Object.values(row).some(value => value !== undefined && value !== '')
    );
    
    console.log('SheetDataTransformer initialized with data:', this.data.length, 'rows');
  }

  toJSON(): Record<string, any>[] {
    return this.data;
  }

  toCSV(): string {
    if (this.data.length === 0) return '';
    
    const headers = Object.keys(this.data[0]);
    const csvRows = [
      headers.join(','),
      ...this.data.map(row =>
        headers.map(header => {
          const value = row[header]?.toString() ?? '';
          return value.includes(',') ? `"${value}"` : value;
        }).join(',')
      )
    ];
    
    return csvRows.join('\n');
  }

  filter(predicate: (row: Record<string, any>) => boolean): DataTransformer {
    this.data = this.data.filter(predicate);
    return this;
  }

  map(transform: (row: Record<string, any>) => Record<string, any>): DataTransformer {
    this.data = this.data.map(transform);
    return this;
  }

  groupBy(key: string): Record<string, Record<string, any>[]> {
    return this.data.reduce((groups, row) => {
      const groupKey = row[key];
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(row);
      return groups;
    }, {} as Record<string, Record<string, any>[]>);
  }

  aggregate(groupKey: string, aggregations: Record<string, (values: any[]) => any>): Record<string, any>[] {
    const groups = this.groupBy(groupKey);
    
    return Object.entries(groups).map(([key, rows]) => {
      const result: Record<string, any> = { [groupKey]: key };
      
      Object.entries(aggregations).forEach(([field, fn]) => {
        result[field] = fn(rows.map(row => row[field]));
      });
      
      return result;
    });
  }

  // New methods for enhanced reporting capabilities
  summarize(metrics: Record<string, (data: any[]) => any>): Record<string, any> {
    const summary: Record<string, any> = {};
    
    Object.entries(metrics).forEach(([name, calculator]) => {
      summary[name] = calculator(this.data);
    });
    
    return summary;
  }

  pivotTable(rowKey: string, colKey: string, valueKey: string, aggregator: (values: any[]) => any): Record<string, Record<string, any>> {
    const pivot: Record<string, Record<string, any>> = {};
    const uniqueColumns = new Set(this.data.map(row => row[colKey]));
    
    const groupedRows = this.groupBy(rowKey);
    
    Object.entries(groupedRows).forEach(([rowValue, rows]) => {
      pivot[rowValue] = {};
      uniqueColumns.forEach(colValue => {
        const relevantRows = rows.filter(row => row[colKey] === colValue);
        pivot[rowValue][colValue as string] = aggregator(relevantRows.map(row => row[valueKey]));
      });
    });
    
    return pivot;
  }

  timeSeries(dateKey: string, valueKey: string, interval: 'day' | 'week' | 'month' = 'day'): Record<string, any>[] {
    const sorted = [...this.data].sort((a, b) => new Date(a[dateKey]).getTime() - new Date(b[dateKey]).getTime());
    const series: Record<string, any>[] = [];
    
    if (sorted.length === 0) return series;
    
    let currentDate = new Date(sorted[0][dateKey]);
    const lastDate = new Date(sorted[sorted.length - 1][dateKey]);
    
    while (currentDate <= lastDate) {
      const nextDate = new Date(currentDate);
      switch (interval) {
        case 'day':
          nextDate.setDate(nextDate.getDate() + 1);
          break;
        case 'week':
          nextDate.setDate(nextDate.getDate() + 7);
          break;
        case 'month':
          nextDate.setMonth(nextDate.getMonth() + 1);
          break;
      }
      
      const periodData = sorted.filter(row => {
        const rowDate = new Date(row[dateKey]);
        return rowDate >= currentDate && rowDate < nextDate;
      });
      
      series.push({
        period: currentDate.toISOString().split('T')[0],
        value: periodData.reduce((sum, row) => sum + (parseFloat(row[valueKey]) || 0), 0),
        count: periodData.length
      });
      
      currentDate = nextDate;
    }
    
    return series;
  }

  calculateStatistics(valueKey: string): Record<string, number> {
    const values = this.data.map(row => parseFloat(row[valueKey])).filter(v => !isNaN(v));
    const n = values.length;
    
    if (n === 0) return {
      min: 0,
      max: 0,
      mean: 0,
      median: 0,
      stdDev: 0
    };
    
    const sorted = [...values].sort((a, b) => a - b);
    const sum = values.reduce((a, b) => a + b, 0);
    const mean = sum / n;
    const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / n;
    
    return {
      min: sorted[0],
      max: sorted[n - 1],
      mean,
      median: n % 2 === 0 ? (sorted[n/2 - 1] + sorted[n/2]) / 2 : sorted[Math.floor(n/2)],
      stdDev: Math.sqrt(variance)
    };
  }
}

// Utility functions for aggregations
export const aggregations = {
  sum: (values: number[]) => values.reduce((a, b) => a + (Number(b) || 0), 0),
  avg: (values: number[]) => values.reduce((a, b) => a + (Number(b) || 0), 0) / values.length,
  max: (values: number[]) => Math.max(...values.map(v => Number(v) || 0)),
  min: (values: number[]) => Math.min(...values.map(v => Number(v) || 0)),
  count: (values: any[]) => values.length,
};

export async function createSheetDataTransformer(spreadsheetId: string, range: string): Promise<SheetDataTransformer> {
  const data = await fetchSheetData(spreadsheetId, range);
  return new SheetDataTransformer(data);
}