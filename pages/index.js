import Head from 'next/head';
import Link from 'next/link';
import React from 'react';
import Footer from '../components/Footer';

export default function Home() {
  return (
    <>
      <Head>
        <title>Mooshi</title>
        <meta name="viewport" content="initial-scale=1.0, width=device-width" />
        <meta name="description" content="Mooshi's personal website."></meta>
        {/* /google */}
        <meta name='og:description' content="Mooshi's personal website."></meta> 
        {/* discord */}
      </Head>

      <div className='text-6xl text-center w-screen h-screen text-white bg-neutral-700'>      
        <div className='inline-block' id="title">
          hi
        </div>
        <div id="navbar" className="text-primary bg-green-800">
          Test
        </div>
        <Link href='/about'>
          <button className='bg-green-800 text-white rounded-md'>About</button>
        </Link>

      </div>
      <Footer />
    </>
  )
}
