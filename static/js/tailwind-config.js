// Tailwind CSS configuration
if (typeof tailwind !== 'undefined') {
  tailwind.config = {
    darkMode: 'class',
    theme: {
      extend: {
        fontFamily: {
          'outfit': ['Outfit', 'sans-serif'],
        },
        colors: {
          'primary': {
            DEFAULT: '#465fff',
            dark: '#3641f5',
            light: '#7592ff',
          },
          'brand': {
            25: '#f2f7ff',
            50: '#ecf3ff',
            100: '#dde9ff',
            200: '#c2d6ff',
            300: '#9cb9ff',
            400: '#7592ff',
            500: '#465fff',
            600: '#3641f5',
            700: '#2a31d8',
            800: '#252dae',
            900: '#262e89',
            950: '#161950',
          },
          'success': {
            25: '#f6fef9',
            50: '#ecfdf3',
            100: '#d1fadf',
            200: '#a6f4c5',
            300: '#6ce9a6',
            400: '#32d583',
            500: '#12b76a',
            600: '#039855',
            700: '#027a48',
            800: '#05603a',
            900: '#054f31',
          },
          'error': {
            25: '#fffbfa',
            50: '#fef3f2',
            100: '#fee4e2',
            200: '#fecdca',
            300: '#fda29b',
            400: '#f97066',
            500: '#f04438',
            600: '#d92d20',
            700: '#b42318',
            800: '#912018',
            900: '#7a271a',
          },
          'warning': {
            25: '#fffcf5',
            50: '#fffaeb',
            100: '#fef0c7',
            200: '#fedf89',
            300: '#fec84b',
            400: '#fdb022',
            500: '#f79009',
            600: '#dc6803',
            700: '#b54708',
            800: '#93370d',
            900: '#7a2e0e',
          },
        },
      },
    },
  };
}
